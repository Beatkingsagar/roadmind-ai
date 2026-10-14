"""Traffic speed prediction model supporting explicit forecast intervals and abstention reasons."""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(64), primary_key=True)
    segment_id = Column(String(64), ForeignKey("road_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chronological timestamps
    issue_time = Column(UTCDateTime, nullable=False, index=True)  # Time forecast was calculated
    target_time = Column(UTCDateTime, nullable=False, index=True)  # Time horizon (e.g. +15m, +30m)
    horizon_minutes = Column(Integer, nullable=False)  # 15 or 30
    
    model_version = Column(String(64), default="historical_median_v1", nullable=False)
    input_snapshot_reference = Column(String(64), nullable=False)  # Hash or snapshot timestamp
    
    # Predicted speed (meters per second)
    predicted_speed_mps = Column(Float, nullable=True)
    interval_lower_mps = Column(Float, nullable=True)  # Prediction interval lower bound
    interval_upper_mps = Column(Float, nullable=True)  # Prediction interval upper bound
    confidence_level = Column(Float, default=0.90, nullable=False)
    
    # Explicit abstention: return reason instead of inventing numbers
    # Reasons: INSUFFICIENT_HISTORY, STALE_OBSERVATIONS, UNOBSERVED_SEGMENT, INVALID_UNITS
    abstention_reason = Column(String(64), nullable=True)
    data_mode = Column(String(32), default="synthetic", nullable=False)

    # Relationships
    segment = relationship("RoadSegment", back_populates="predictions")
    evaluation = relationship("OutcomeEvaluation", back_populates="prediction", uselist=False)

    __table_args__ = (
        Index("idx_pred_target", "segment_id", "target_time"),
    )

    @property
    def is_abstained(self) -> bool:
        return self.abstention_reason is not None or self.predicted_speed_mps is None

    def __repr__(self) -> str:
        if self.is_abstained:
            return f"<Prediction id={self.id} seg={self.segment_id} target={self.target_time} ABSTAINED: {self.abstention_reason}>"
        return f"<Prediction id={self.id} seg={self.segment_id} target={self.target_time} pred={self.predicted_speed_mps}mps>"
