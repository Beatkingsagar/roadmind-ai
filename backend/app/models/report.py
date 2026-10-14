"""Incident report model with dependency grouping and idempotency support."""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(64), primary_key=True)
    incident_type = Column(String(32), nullable=False)  # accident, pothole, road_damage, debris, flooding, stall
    
    # Temporal fields
    claimed_event_time = Column(UTCDateTime, nullable=False)  # Claimed by reporter
    submitted_at = Column(UTCDateTime, default=utc_now, nullable=False)  # Time recorded
    available_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)  # Replay visibility
    
    # Location
    segment_id = Column(String(64), ForeignKey("road_segments.id"), nullable=False, index=True)
    location_description = Column(String(256), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Source & Dependency Grouping (shared-source reports grouped to prevent support inflation)
    reporter_reference = Column(String(64), nullable=False)
    dependency_group_id = Column(String(64), nullable=True, index=True)  # Shared source identifier
    
    description = Column(Text, nullable=False)
    data_mode = Column(String(32), default="user_submitted", nullable=False)  # user_submitted, synthetic
    idempotency_key = Column(String(64), unique=True, nullable=True, index=True)
    
    # Optional clustering to an incident episode
    episode_id = Column(String(64), ForeignKey("incident_episodes.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    segment = relationship("RoadSegment", back_populates="reports")
    evidence_items = relationship("Evidence", back_populates="report", cascade="all, delete-orphan")
    episode = relationship("IncidentEpisode", back_populates="reports")

    __table_args__ = (
        Index("idx_reports_replay", "available_at", "segment_id"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} type={self.incident_type} seg={self.segment_id} group={self.dependency_group_id}>"
