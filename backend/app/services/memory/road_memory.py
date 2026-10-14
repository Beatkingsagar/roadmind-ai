"""Road Memory and Inspection Priority Engine.

Implements:
1. Spatiotemporal Clustering of Reports into Distinct Incident Episodes:
   - Groups overlapping reports by location (segment or spatial radius) and time window.
   - Prevents duplicate reports from being counted as separate road failures.
2. Duplicate-Aware Recurrence and Duration Summaries:
   - Measures observed recurrence (episode count) rather than raw report volume.
   - Explicitly notes that without exposure data, this reflects observed recurrence, not per-vehicle risk.
3. Observation Coverage Reporting:
   - Evaluates sensor density and temporal span.
   - Explicitly flags poor coverage so absence of reports is not mistaken for safety.
4. Transparent Inspection Priority Ranking:
   - Clear, deterministic scoring rubric with complete component explanations.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.models import Observation, Report, RoadSegment
from backend.app.schemas.memory import (
    EpisodeCluster,
    InspectionPriority,
    ObservationCoverage,
    SegmentMemorySummary,
)

INSPECTION_RUBRIC_VERSION = "inspection_v1.0"
DEFAULT_SPATIAL_THRESHOLD_METERS = 300.0
DEFAULT_TEMPORAL_THRESHOLD_HOURS = 4.0
MIN_OBSERVATIONS_FOR_GOOD_COVERAGE = 5

SEVERITY_WEIGHTS = {
    "critical": 25.0,
    "high": 20.0,
    "medium": 12.0,
    "low": 5.0,
    "none": 0.0,
}


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def cluster_reports_into_episodes(
    reports: List[Report],
    replay_time: Optional[datetime] = None,
    spatial_threshold_meters: float = DEFAULT_SPATIAL_THRESHOLD_METERS,
    temporal_threshold_hours: float = DEFAULT_TEMPORAL_THRESHOLD_HOURS,
) -> List[EpisodeCluster]:
    """Cluster raw reports into distinct spatiotemporal incident episodes.
    
    A report is added to an active episode if:
    - Same segment_id OR geographic distance <= spatial_threshold_meters
    - AND event time difference <= temporal_threshold_hours
    - AND matching incident type
    """
    replay_utc = _ensure_utc(replay_time) if replay_time else None

    # Filter temporally eligible reports
    eligible_reports = [
        r for r in reports
        if replay_utc is None or _ensure_utc(r.available_at) <= replay_utc
    ]

    # Sort reports chronologically by claimed event time
    sorted_reports = sorted(eligible_reports, key=lambda r: _ensure_utc(r.claimed_event_time))

    # Mutable tracking list for building clusters
    raw_clusters: List[Dict[str, Any]] = []

    for rep in sorted_reports:
        rep_time = _ensure_utc(rep.claimed_event_time)
        matched_cluster = None

        for cluster in raw_clusters:
            # Check segment or spatial distance
            same_segment = cluster["segment_id"] == rep.segment_id
            dist_meters = haversine_distance_meters(
                cluster["center_lat"], cluster["center_lon"], rep.latitude, rep.longitude
            )
            spatial_match = same_segment or (dist_meters <= spatial_threshold_meters)

            # Check temporal window relative to cluster's last reported time
            hours_diff = abs((rep_time - cluster["last_reported_at"]).total_seconds()) / 3600.0
            temporal_match = hours_diff <= temporal_threshold_hours

            # Incident type match
            type_match = cluster["episode_type"] == rep.incident_type

            if spatial_match and temporal_match and type_match:
                matched_cluster = cluster
                break

        if matched_cluster:
            # Merge report into existing cluster
            matched_cluster["report_ids"].append(rep.id)
            matched_cluster["reporters"].add(rep.reporter_reference)
            if rep.dependency_group_id:
                matched_cluster["dependency_groups"].add(rep.dependency_group_id)

            if rep_time > matched_cluster["last_reported_at"]:
                matched_cluster["last_reported_at"] = rep_time
            if rep_time < matched_cluster["first_reported_at"]:
                matched_cluster["first_reported_at"] = rep_time
        else:
            # Create a new distinct incident episode
            cluster_id = f"ep_{uuid.uuid4().hex[:8]}"
            raw_clusters.append({
                "id": cluster_id,
                "segment_id": rep.segment_id,
                "center_lat": rep.latitude,
                "center_lon": rep.longitude,
                "episode_type": rep.incident_type,
                "first_reported_at": rep_time,
                "last_reported_at": rep_time,
                "severity_level": "medium",  # default
                "report_ids": [rep.id],
                "reporters": {rep.reporter_reference},
                "dependency_groups": {rep.dependency_group_id} if rep.dependency_group_id else set(),
            })

    # Convert to EpisodeCluster Pydantic objects
    results: List[EpisodeCluster] = []
    for c in raw_clusters:
        first_t = c["first_reported_at"]
        last_t = c["last_reported_at"]
        duration_mins = max(0.0, round((last_t - first_t).total_seconds() / 60.0, 1))

        results.append(
            EpisodeCluster(
                id=c["id"],
                segment_id=c["segment_id"],
                episode_type=c["episode_type"],
                first_reported_at=first_t,
                last_reported_at=last_t,
                duration_minutes=duration_mins,
                severity_level=c["severity_level"],
                report_count=len(c["report_ids"]),
                report_ids=c["report_ids"],
                unique_source_count=len(c["reporters"]),
                dependency_group_ids=sorted(list(c["dependency_groups"])),
            )
        )

    return results


def compute_observation_coverage(
    observations: List[Observation],
    segment_id: str,
    replay_time: Optional[datetime] = None,
    min_observations_threshold: int = MIN_OBSERVATIONS_FOR_GOOD_COVERAGE,
) -> ObservationCoverage:
    """Analyze sensor observation coverage and identify sparse/unobserved limitations."""
    replay_utc = _ensure_utc(replay_time) if replay_time else None

    eligible_obs = [
        o for o in observations
        if o.segment_id == segment_id and (replay_utc is None or _ensure_utc(o.available_at) <= replay_utc)
    ]

    count = len(eligible_obs)
    if count == 0:
        return ObservationCoverage(
            segment_id=segment_id,
            observation_count=0,
            first_observation_time=None,
            latest_observation_time=None,
            coverage_span_hours=0.0,
            is_coverage_poor=True,
            coverage_limitation_note="No sensor observations available. The absence of incident reports cannot be interpreted as road safety or free-flow reliability.",
        )

    eligible_obs.sort(key=lambda o: _ensure_utc(o.observed_at))
    first_time = _ensure_utc(eligible_obs[0].observed_at)
    latest_time = _ensure_utc(eligible_obs[-1].observed_at)
    span_hours = round(max(0.0, (latest_time - first_time).total_seconds() / 3600.0), 2)

    is_poor = count < min_observations_threshold
    note = None
    if is_poor:
        note = f"Sparse observation coverage ({count} observations over {span_hours}h). Ground truth conditions remain largely unverified by physical sensors."

    return ObservationCoverage(
        segment_id=segment_id,
        observation_count=count,
        first_observation_time=first_time,
        latest_observation_time=latest_time,
        coverage_span_hours=span_hours,
        is_coverage_poor=is_poor,
        coverage_limitation_note=note,
    )


def build_segment_memory_summaries(
    segments: List[RoadSegment],
    reports: List[Report],
    observations: List[Observation],
    replay_time: Optional[datetime] = None,
    spatial_threshold_meters: float = DEFAULT_SPATIAL_THRESHOLD_METERS,
    temporal_threshold_hours: float = DEFAULT_TEMPORAL_THRESHOLD_HOURS,
) -> List[SegmentMemorySummary]:
    """Aggregate memory summaries per road segment with duplicate-aware recurrence."""
    episodes = cluster_reports_into_episodes(
        reports,
        replay_time=replay_time,
        spatial_threshold_meters=spatial_threshold_meters,
        temporal_threshold_hours=temporal_threshold_hours,
    )

    summaries: List[SegmentMemorySummary] = []

    for seg in segments:
        seg_episodes = [ep for ep in episodes if ep.segment_id == seg.id]
        recurrence_count = len(seg_episodes)
        total_reports = sum(ep.report_count for ep in seg_episodes)
        dup_reports = max(0, total_reports - recurrence_count)

        if recurrence_count > 0:
            avg_duration = round(sum(ep.duration_minutes for ep in seg_episodes) / recurrence_count, 1)
            # Find maximum severity
            severities = [ep.severity_level for ep in seg_episodes]
            if "critical" in severities:
                max_sev = "critical"
            elif "high" in severities:
                max_sev = "high"
            elif "medium" in severities:
                max_sev = "medium"
            else:
                max_sev = "low"
        else:
            avg_duration = 0.0
            max_sev = "none"

        coverage = compute_observation_coverage(
            observations, seg.id, replay_time=replay_time
        )

        summaries.append(
            SegmentMemorySummary(
                segment_id=seg.id,
                segment_name=seg.name,
                observed_recurrence_count=recurrence_count,
                total_report_count=total_reports,
                duplicate_or_shared_reports_count=dup_reports,
                average_episode_duration_minutes=avg_duration,
                max_severity=max_sev,
                episodes=seg_episodes,
                observation_coverage=coverage,
            )
        )

    return summaries


def rank_inspection_priorities(
    summaries: List[SegmentMemorySummary],
    rubric_version: str = INSPECTION_RUBRIC_VERSION,
) -> List[InspectionPriority]:
    """Rank road segments by inspection priority with transparent, explainable scoring."""
    unranked: List[Dict[str, Any]] = []

    for s in summaries:
        # 1. Recurrence Component: up to 40 points (15 pts per distinct incident episode)
        rec_pts = min(40.0, s.observed_recurrence_count * 15.0)

        # 2. Severity Component: up to 25 points
        sev_pts = SEVERITY_WEIGHTS.get(s.max_severity, 0.0)

        # 3. Duration Component: up to 20 points (e.g. 10 pts per hour of average duration)
        dur_pts = min(20.0, round((s.average_episode_duration_minutes / 60.0) * 10.0, 1))

        # 4. Coverage Uncertainty Component: 15 points if coverage is poor (needs inspection to verify safety)
        cov_pts = 15.0 if s.observation_coverage.is_coverage_poor else 0.0

        total_score = min(100.0, round(rec_pts + sev_pts + dur_pts + cov_pts, 1))

        # Explicit limitations
        limitations = [
            "Vehicle exposure data unavailable: metric reflects observed recurrence count, not per-vehicle risk."
        ]
        if s.observation_coverage.is_coverage_poor and s.observation_coverage.coverage_limitation_note:
            limitations.append(s.observation_coverage.coverage_limitation_note)

        # Explainable breakdown string
        explanation = (
            f"Inspection Priority: {total_score:.1f}/100. "
            f"Recurrence: {rec_pts:.1f}pts ({s.observed_recurrence_count} distinct episodes, {s.total_report_count} total reports); "
            f"Severity: {sev_pts:.1f}pts (level: {s.max_severity}); "
            f"Duration: {dur_pts:.1f}pts (avg: {s.average_episode_duration_minutes:.1f}m); "
            f"Coverage Uncertainty: {cov_pts:.1f}pts ({'poor' if s.observation_coverage.is_coverage_poor else 'sufficient'})."
        )

        unranked.append({
            "segment_id": s.segment_id,
            "segment_name": s.segment_name,
            "priority_score": total_score,
            "observed_recurrence_score": rec_pts,
            "severity_score": sev_pts,
            "duration_score": dur_pts,
            "coverage_uncertainty_score": cov_pts,
            "scoring_rubric_version": rubric_version,
            "explanation": explanation,
            "data_limitations": limitations,
            "observed_recurrence_count": s.observed_recurrence_count,
        })

    # Sort descending by priority_score, then observed_recurrence_count
    unranked.sort(
        key=lambda item: (item["priority_score"], item["observed_recurrence_count"]),
        reverse=True,
    )

    ranked: List[InspectionPriority] = []
    for rank_idx, item in enumerate(unranked, start=1):
        ranked.append(
            InspectionPriority(
                segment_id=item["segment_id"],
                segment_name=item["segment_name"],
                priority_score=item["priority_score"],
                priority_rank=rank_idx,
                observed_recurrence_score=item["observed_recurrence_score"],
                severity_score=item["severity_score"],
                duration_score=item["duration_score"],
                coverage_uncertainty_score=item["coverage_uncertainty_score"],
                scoring_rubric_version=item["scoring_rubric_version"],
                explanation=f"[Rank {rank_idx}] " + item["explanation"],
                data_limitations=item["data_limitations"],
            )
        )

    return ranked
