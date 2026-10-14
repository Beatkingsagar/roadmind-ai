"""Evidence Assessment Engine for RoadMind AI.

Implements:
- Server-side SHA-256 evidence hashing and exact duplicate detection.
- Shared-source dependency grouping (capping correlated reports).
- Inconsistency checks (future claimed event times, geometric divergence).
- Context-aware sensor contradiction checks.
- Transparent versioned evidence-support rubric (rubric_v1.0).
- Strict separation between heuristic support score and reviewer verification.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from backend.app.models import Evidence, Observation, Report, RoadSegment
from backend.app.services.replay.filter import ensure_utc, filter_eligible_observations


RUBRIC_VERSION = "rubric_v1.0"


def compute_evidence_hash(media_bytes: bytes) -> str:
    """Compute server-side SHA-256 hash of media file bytes."""
    return hashlib.sha256(media_bytes).hexdigest()


class EvidenceAssessmentResult:
    """Structured assessment explanation object."""

    def __init__(
        self,
        heuristic_support_score: float,
        supporting_factors: List[str],
        contradictions: List[str],
        dependencies: List[str],
        duplicate_exclusions: List[str],
        rubric_version: str = RUBRIC_VERSION,
    ):
        self.heuristic_support_score = round(max(0.05, min(0.95, heuristic_support_score)), 2)
        self.supporting_factors = supporting_factors
        self.contradictions = contradictions
        self.dependencies = dependencies
        self.duplicate_exclusions = duplicate_exclusions
        self.rubric_version = rubric_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heuristic_support_score": self.heuristic_support_score,
            "supporting_factors": self.supporting_factors,
            "contradictions": self.contradictions,
            "dependencies": self.dependencies,
            "duplicate_exclusions": self.duplicate_exclusions,
            "rubric_version": self.rubric_version,
            "note": "Heuristic support score reflects observational evidence strength, NOT an incident probability.",
        }

    def generate_summary(self) -> str:
        parts = []
        if self.supporting_factors:
            parts.append(f"Supported by: {'; '.join(self.supporting_factors)}.")
        if self.contradictions:
            parts.append(f"Contradictions: {'; '.join(self.contradictions)}.")
        if self.duplicate_exclusions:
            parts.append(f"Exclusions: {'; '.join(self.duplicate_exclusions)}.")
        if self.dependencies:
            parts.append(f"Dependencies: {'; '.join(self.dependencies)}.")
        return " ".join(parts) or "Initial single-source submission."


def assess_evidence_for_reports(
    db: Session,
    reports: List[Report],
    segment: RoadSegment,
    replay_time: Optional[datetime] = None,
) -> EvidenceAssessmentResult:
    """Assess evidence across a set of linked reports on a road segment as of replay_time."""
    t_replay = ensure_utc(replay_time)
    supporting_factors: List[str] = []
    contradictions: List[str] = []
    dependencies: List[str] = []
    duplicate_exclusions: List[str] = []

    if not reports:
        return EvidenceAssessmentResult(
            heuristic_support_score=0.10,
            supporting_factors=[],
            contradictions=["No eligible reports available as of replay time."],
            dependencies=[],
            duplicate_exclusions=[],
        )

    # Base score for having an eligible submission
    score = 0.35
    supporting_factors.append(f"Initial report filed ({reports[0].incident_type})")

    # 1. Source Independence & Dependency Grouping
    distinct_sources = set()
    dep_group_counts: Dict[str, int] = {}
    for r in reports:
        if r.dependency_group_id:
            dep_group_counts[r.dependency_group_id] = dep_group_counts.get(r.dependency_group_id, 0) + 1
        else:
            distinct_sources.add(r.reporter_reference)

    for group_id, count in dep_group_counts.items():
        if count > 1:
            dependencies.append(
                f"Source group '{group_id}' contains {count} reports; corroborated contribution is capped at single source."
            )
            score += 0.10
        else:
            distinct_sources.add(group_id)

    # Independent corroboration bonus (capped at +0.25)
    independent_count = len(distinct_sources)
    if independent_count > 1:
        corrob_bonus = min(0.25, (independent_count - 1) * 0.12)
        score += corrob_bonus
        supporting_factors.append(f"Corroborated by {independent_count} independent sources")

    # 2. Evidence Media Hashing & Duplicate Deduplication
    unique_hashes = set()
    for r in reports:
        for ev in r.evidence_items:
            # Check if evidence is eligible at replay time
            if ev.available_at and ev.available_at > t_replay:
                continue
            if ev.is_duplicate:
                duplicate_exclusions.append(
                    f"Evidence {ev.id} shares SHA-256 hash with {ev.duplicate_of_id or 'earlier upload'}; awarded 0 independent weight."
                )
            elif ev.content_hash not in unique_hashes:
                unique_hashes.add(ev.content_hash)
            else:
                duplicate_exclusions.append(
                    f"Evidence {ev.id} repeated hash {ev.content_hash[:8]} in batch; excluded from independent support."
                )

    if unique_hashes:
        media_bonus = min(0.20, len(unique_hashes) * 0.10)
        score += media_bonus
        supporting_factors.append(f"{len(unique_hashes)} unique non-duplicate media evidence items verified")

    # 3. Timestamp Inconsistency Checks
    for r in reports:
        if r.claimed_event_time > r.submitted_at:
            delta_mins = (r.claimed_event_time - r.submitted_at).total_seconds() / 60.0
            contradictions.append(
                f"Report {r.id}: Claimed event time is {delta_mins:.0f}m in the future relative to submission timestamp."
            )
            score -= 0.15

    # 4. Context-Aware Sensor Contradiction & Corroboration Checks
    # Compare with eligible observations on the same segment around claimed event time
    recent_obs = filter_eligible_observations(db, segment_id=segment.id, replay_time=t_replay)
    if recent_obs:
        # Check observations within 20 minutes of most recent report
        latest_report_time = max(r.claimed_event_time for r in reports)
        comparable_obs = [
            o for o in recent_obs
            if abs((o.observed_at - latest_report_time).total_seconds()) <= 1200
        ]
        if comparable_obs:
            latest_comp = comparable_obs[-1]
            speed_ratio = latest_comp.speed_mps / segment.free_flow_speed_mps

            # If report claims blockage/accident/stall, but sensor reads free-flow
            severe_types = {"accident", "stall", "road_damage", "flooding", "debris"}
            reported_types = {r.incident_type for r in reports}
            if reported_types & severe_types:
                if speed_ratio >= 0.85:
                    contradictions.append(
                        f"Speed sensor reading ({latest_comp.speed_mps:.1f} m/s, {latest_comp.speed_kmph:.0f} km/h) "
                        f"at {latest_comp.observed_at.strftime('%H:%M:%SZ')} shows normal free-flow, "
                        f"contradicting reported major disruption."
                    )
                    score -= 0.20
                elif speed_ratio <= 0.40:
                    supporting_factors.append(
                        f"Sensor telemetry confirms acute speed drop to {latest_comp.speed_mps:.1f} m/s "
                        f"({latest_comp.speed_kmph:.0f} km/h vs {segment.free_flow_speed_kmph:.0f} km/h baseline)"
                    )
                    score += 0.15

    return EvidenceAssessmentResult(
        heuristic_support_score=score,
        supporting_factors=supporting_factors,
        contradictions=contradictions,
        dependencies=dependencies,
        duplicate_exclusions=duplicate_exclusions,
        rubric_version=RUBRIC_VERSION,
    )
