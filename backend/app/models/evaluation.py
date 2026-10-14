"""Outcome evaluation model for comparing immutable predictions against revealed actuals."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class OutcomeEvaluation(Base):
    __tablename__ = "outcome_evaluations"

    id = Column(String(64), primary_key=True)
    prediction_id = Column(String(64), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    observation_id = Column(String(64), ForeignKey("observations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Error metrics (predicted - actual)
    error_speed_mps = Column(Float, nullable=False)
    absolute_error_mps = Column(Float, nullable=False)
    within_interval = Column(Boolean, nullable=False)
    
    evaluated_at = Column(UTCDateTime, default=utc_now, nullable=False)
    evaluation_version = Column(String(32), default="eval_v1.0", nullable=False)

    # Relationships
    prediction = relationship("Prediction", back_populates="evaluation")
    observation = relationship("Observation", back_populates="evaluations")

    __table_args__ = (
        Index("idx_eval_metric", "evaluation_version", "within_interval"),
    )

    def __repr__(self) -> str:
        return f"<OutcomeEvaluation id={self.id} pred={self.prediction_id} abs_err={self.absolute_error_mps:.2f}mps inside={self.within_interval}>"
