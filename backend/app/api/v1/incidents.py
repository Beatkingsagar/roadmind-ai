"""Incident episodes and operator review audit API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, parse_temporal_at, verify_reviewer_auth
from backend.app.models import IncidentEpisode, IncidentReview, Report
from backend.app.schemas.evidence import EvidenceResponse
from backend.app.schemas.incident import (
    IncidentEpisodeDetailResponse,
    IncidentEpisodeResponse,
    IncidentReviewCreate,
    IncidentReviewResponse,
)
from backend.app.schemas.report import ReportResponse
from backend.app.services.replay.filter import (
    ensure_utc,
    filter_eligible_episodes,
    filter_eligible_evidence,
    filter_eligible_reports,
    filter_eligible_reviews,
)

router = APIRouter(tags=["Incidents & Operator Reviews"])


@router.get(
    "/incidents",
    response_model=List[IncidentEpisodeResponse],
    summary="List active or historical incident episodes subject to temporal replay filtering",
)
def list_incidents(
    at: datetime = Depends(parse_temporal_at),
    segment_id: Optional[str] = Query(None, description="Filter by primary road segment ID"),
    lifecycle_status: Optional[str] = Query(None, description="Filter by lifecycle status (reported, triaged, resolved, etc.)"),
    db: Session = Depends(get_db),
) -> List[IncidentEpisodeResponse]:
    """Retrieve incident episodes visible as of replay time 'at'.

    Guarantees:
    - Episodes first reported after 'at' are strictly excluded.
    - Report counts only reflect reports available at or before 'at'.
    """
    t_replay = ensure_utc(at)
    episodes = filter_eligible_episodes(db, segment_id=segment_id, replay_time=t_replay)

    if lifecycle_status:
        episodes = [ep for ep in episodes if ep.lifecycle_status == lifecycle_status]

    response_items = []
    for ep in episodes:
        eligible_reps = [r for r in ep.reports if ensure_utc(r.available_at) <= t_replay]
        response_items.append(
            IncidentEpisodeResponse(
                id=ep.id,
                primary_segment_id=ep.primary_segment_id,
                affected_segments=ep.affected_segments,
                episode_type=ep.episode_type,
                first_reported_at=ep.first_reported_at,
                last_reported_at=ep.last_reported_at,
                lifecycle_status=ep.lifecycle_status,
                severity_level=ep.severity_level,
                heuristic_support_score=ep.heuristic_support_score,
                assessment_summary=ep.assessment_summary,
                rubric_version=ep.rubric_version,
                reviewer_state=ep.reviewer_state,
                report_count=len(eligible_reps),
            )
        )

    return response_items


@router.get(
    "/incidents/{id}",
    response_model=IncidentEpisodeDetailResponse,
    summary="Get incident episode detail with temporally eligible reports and reviewer history",
)
def get_incident_detail(
    id: str,
    at: datetime = Depends(parse_temporal_at),
    db: Session = Depends(get_db),
) -> IncidentEpisodeDetailResponse:
    """Retrieve detailed view of an incident episode.

    Temporal Replay Behavior:
    - Reports or reviews available after 'at' are hidden.
    - Returns 404 if the episode was first reported after 'at'.
    """
    t_replay = ensure_utc(at)
    episode = db.query(IncidentEpisode).filter(IncidentEpisode.id == id).first()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident episode '{id}' not found.",
        )

    if ensure_utc(episode.first_reported_at) > t_replay:
        # Incident not yet reported as of replay time
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident episode '{id}' was not yet reported as of {t_replay.isoformat()}.",
        )

    # Filter reports and reviews strictly up to replay time
    eligible_reports = [r for r in episode.reports if ensure_utc(r.available_at) <= t_replay]
    eligible_reviews = [rev for rev in episode.reviews if ensure_utc(rev.available_at) <= t_replay]

    serialized_reports: List[ReportResponse] = []
    for rep in eligible_reports:
        eligible_ev = [ev for ev in rep.evidence_items if ensure_utc(ev.available_at) <= t_replay]
        serialized_reports.append(
            ReportResponse(
                id=rep.id,
                incident_type=rep.incident_type,
                claimed_event_time=rep.claimed_event_time,
                submitted_at=rep.submitted_at,
                available_at=rep.available_at,
                segment_id=rep.segment_id,
                location_description=rep.location_description,
                latitude=rep.latitude,
                longitude=rep.longitude,
                reporter_reference=rep.reporter_reference,
                dependency_group_id=rep.dependency_group_id,
                description=rep.description,
                data_mode=rep.data_mode,
                idempotency_key=rep.idempotency_key,
                episode_id=rep.episode_id,
                evidence_items=[EvidenceResponse.model_validate(ev) for ev in eligible_ev],
            )
        )

    return IncidentEpisodeDetailResponse(
        id=episode.id,
        primary_segment_id=episode.primary_segment_id,
        affected_segments=episode.affected_segments,
        episode_type=episode.episode_type,
        first_reported_at=episode.first_reported_at,
        last_reported_at=episode.last_reported_at,
        lifecycle_status=episode.lifecycle_status,
        severity_level=episode.severity_level,
        heuristic_support_score=episode.heuristic_support_score,
        assessment_summary=episode.assessment_summary,
        rubric_version=episode.rubric_version,
        reviewer_state=episode.reviewer_state,
        report_count=len(serialized_reports),
        reports=serialized_reports,
        reviews=[IncidentReviewResponse.model_validate(rev) for rev in eligible_reviews],
    )


@router.post(
    "/incidents/{id}/reviews",
    response_model=IncidentReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an operator review with authorization boundary check and audit trail persistence",
)
def submit_incident_review(
    id: str,
    body: IncidentReviewCreate,
    operator_role: str = Depends(verify_reviewer_auth),
    db: Session = Depends(get_db),
) -> IncidentReview:
    """Submit a verified traffic operator decision on an incident.

    Security & Separation Rules:
    - Protected by reviewer authorization header (403 if unauthenticated).
    - Reviewer decisions are stored in an append-only audit trail and modify
      'reviewer_state', keeping heuristic evidence scores untouched.
    """
    episode = db.query(IncidentEpisode).filter(IncidentEpisode.id == id).first()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident episode '{id}' not found.",
        )

    now = datetime.now(timezone.utc)
    review_id = f"rev_{uuid.uuid4().hex[:8]}"
    prev_state = episode.reviewer_state

    review = IncidentReview(
        id=review_id,
        episode_id=episode.id,
        reviewer_reference=f"{body.reviewer_reference} [{operator_role}]",
        decision=body.decision.value,
        reason=body.reason,
        previous_state=prev_state,
        recorded_at=now,
        available_at=now,
    )

    # Transition episode reviewer state
    episode.reviewer_state = body.decision.value
    if body.decision.value == "verified":
        episode.lifecycle_status = "triaged"
    elif body.decision.value == "rejected":
        episode.lifecycle_status = "resolved"

    db.add(review)
    db.commit()
    db.refresh(review)

    return review
