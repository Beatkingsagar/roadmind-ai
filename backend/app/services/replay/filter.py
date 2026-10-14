"""Temporal replay filtering service for RoadMind AI.

Enforces strict temporal eligibility: at replay time T, only records with
available_at <= T may be visible to domain services, forecasts, or operators.
Prevents future observation leakage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models import (
    Evidence,
    IncidentEpisode,
    IncidentReview,
    Observation,
    Report,
)


def ensure_utc(dt: datetime | None) -> datetime:
    """Ensure datetime is timezone-aware UTC. Defaults to current UTC if None."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def filter_eligible_observations(
    db: Session,
    segment_id: Optional[str] = None,
    replay_time: Optional[datetime] = None,
) -> List[Observation]:
    """Retrieve observations eligible as of replay_time (available_at <= replay_time)."""
    t = ensure_utc(replay_time)
    query = db.query(Observation).filter(Observation.available_at <= t)
    if segment_id:
        query = query.filter(Observation.segment_id == segment_id)
    return query.order_by(Observation.observed_at.asc()).all()


def filter_eligible_reports(
    db: Session,
    segment_id: Optional[str] = None,
    replay_time: Optional[datetime] = None,
) -> List[Report]:
    """Retrieve reports eligible as of replay_time (available_at <= replay_time)."""
    t = ensure_utc(replay_time)
    query = db.query(Report).filter(Report.available_at <= t)
    if segment_id:
        query = query.filter(Report.segment_id == segment_id)
    return query.order_by(Report.submitted_at.asc()).all()


def filter_eligible_evidence(
    db: Session,
    report_id: Optional[str] = None,
    replay_time: Optional[datetime] = None,
) -> List[Evidence]:
    """Retrieve evidence eligible as of replay_time (available_at <= replay_time)."""
    t = ensure_utc(replay_time)
    query = db.query(Evidence).filter(Evidence.available_at <= t)
    if report_id:
        query = query.filter(Evidence.report_id == report_id)
    return query.order_by(Evidence.submitted_at.asc()).all()


def filter_eligible_reviews(
    db: Session,
    episode_id: Optional[str] = None,
    replay_time: Optional[datetime] = None,
) -> List[IncidentReview]:
    """Retrieve incident reviews eligible as of replay_time (available_at <= replay_time)."""
    t = ensure_utc(replay_time)
    query = db.query(IncidentReview).filter(IncidentReview.available_at <= t)
    if episode_id:
        query = query.filter(IncidentReview.episode_id == episode_id)
    return query.order_by(IncidentReview.recorded_at.asc()).all()


def filter_eligible_episodes(
    db: Session,
    segment_id: Optional[str] = None,
    replay_time: Optional[datetime] = None,
) -> List[IncidentEpisode]:
    """Retrieve incident episodes first reported at or before replay_time."""
    t = ensure_utc(replay_time)
    query = db.query(IncidentEpisode).filter(IncidentEpisode.first_reported_at <= t)
    if segment_id:
        query = query.filter(IncidentEpisode.primary_segment_id == segment_id)
    return query.order_by(IncidentEpisode.first_reported_at.asc()).all()
