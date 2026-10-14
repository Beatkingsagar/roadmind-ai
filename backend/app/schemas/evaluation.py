"""Outcome evaluation schemas."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OutcomeEvaluationResponse(BaseModel):
    id: str
    prediction_id: str
    observation_id: str
    error_speed_mps: float
    absolute_error_mps: float
    within_interval: bool
    evaluated_at: datetime
    evaluation_version: str

    model_config = ConfigDict(from_attributes=True)


class EvaluationSummary(BaseModel):
    horizon_minutes: int
    sample_count: int
    mae_mps: float
    rmse_mps: float
    interval_coverage_pct: float
    dataset_scope: str
    evaluation_version: str
