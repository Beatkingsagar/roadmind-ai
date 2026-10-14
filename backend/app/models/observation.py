"""Observation model with strict temporal separation between observed_at and available_at."""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(64), primary_key=True)
    segment_id = Column(String(64), ForeignKey("road_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Strict temporal separation:
    # observed_at: The moment the traffic phenomenon physically occurred.
    # available_at: The moment the data record was ingested and became eligible for replay/forecasting.
    observed_at = Column(UTCDateTime, nullable=False, index=True)
    available_at = Column(UTCDateTime, nullable=False, index=True)
    
    # Speed measurement
    value = Column(Float, nullable=False)  # Speed value
    unit = Column(String(16), default="mps", nullable=False)  # "mps" (meters/second) or "kmph"
    quality_score = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0 (signal reliability)
    provenance = Column(String(64), default="synthetic_sensor", nullable=False)
    data_mode = Column(String(32), default="synthetic", nullable=False)

    # Relationships
    segment = relationship("RoadSegment", back_populates="observations")
    evaluations = relationship("OutcomeEvaluation", back_populates="observation")

    __table_args__ = (
        Index("idx_obs_temporal_replay", "segment_id", "available_at"),
    )

    @property
    def speed_mps(self) -> float:
        """Normalized speed in meters per second."""
        if self.unit == "kmph":
            return round(self.value / 3.6, 2)
        return self.value

    @property
    def speed_kmph(self) -> float:
        """Normalized speed in kilometers per hour."""
        if self.unit == "mps":
            return round(self.value * 3.6, 2)
        return self.value

    def __repr__(self) -> str:
        return f"<Observation id={self.id} seg={self.segment_id} val={self.value}{self.unit} obs_at={self.observed_at} avail_at={self.available_at}>"
