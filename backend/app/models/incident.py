"""Incident episode and reviewer audit trail models."""

from __future__ import annotations

import json
from typing import Any, List
from sqlalchemy import Column, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class IncidentEpisode(Base):
    __tablename__ = "incident_episodes"

    id = Column(String(64), primary_key=True)  # e.g. "ep_2026_001"
    primary_segment_id = Column(String(64), ForeignKey("road_segments.id"), nullable=False, index=True)
    affected_segments_json = Column(Text, default="[]", nullable=False)  # List of segment IDs
    episode_type = Column(String(32), default="accident", nullable=False)
    
    first_reported_at = Column(UTCDateTime, nullable=False, index=True)
    last_reported_at = Column(UTCDateTime, nullable=False)
    
    # Lifecycle & Severity
    lifecycle_status = Column(String(32), default="reported", nullable=False)  # reported, triaged, dispatched, in_progress, resolved
    severity_level = Column(String(32), default="medium", nullable=False)  # low, medium, high, critical
    
    # Explainable Evidence Assessment (Heuristic Support Score, NOT a probability)
    heuristic_support_score = Column(Float, default=0.5, nullable=False)
    assessment_summary = Column(Text, nullable=False)
    rubric_version = Column(String(32), default="rubric_v1.0", nullable=False)
    
    # Reviewer decision state (kept strictly separate from heuristic score)
    reviewer_state = Column(String(32), default="unreviewed", nullable=False)  # unreviewed, verified, rejected, disputed

    # Relationships
    reports = relationship("Report", back_populates="episode")
    reviews = relationship("IncidentReview", back_populates="episode", cascade="all, delete-orphan")

    @property
    def affected_segments(self) -> List[str]:
        try:
            return json.loads(self.affected_segments_json)
        except Exception:
            return [self.primary_segment_id]

    def __repr__(self) -> str:
        return f"<IncidentEpisode id={self.id} type={self.episode_type} status={self.lifecycle_status} score={self.heuristic_support_score}>"


class IncidentReview(Base):
    __tablename__ = "incident_reviews"

    id = Column(String(64), primary_key=True)
    episode_id = Column(String(64), ForeignKey("incident_episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_reference = Column(String(64), nullable=False)
    decision = Column(String(32), nullable=False)  # verified, rejected, needs_investigation
    reason = Column(Text, nullable=False)
    previous_state = Column(String(32), nullable=False)
    recorded_at = Column(UTCDateTime, default=utc_now, nullable=False)
    available_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    episode = relationship("IncidentEpisode", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_replay", "episode_id", "available_at"),
    )

    def __repr__(self) -> str:
        return f"<IncidentReview id={self.id} ep={self.episode_id} dec={self.decision}>"
