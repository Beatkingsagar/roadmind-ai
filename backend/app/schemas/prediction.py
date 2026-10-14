"""Forecasting request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import AbstentionReason, DataMode


class PredictionResponse(BaseModel):
    id: str
    segment_id: str
    issue_time: datetime
    target_time: datetime
    horizon_minutes: int
    model_version: str
    input_snapshot_reference: str
    predicted_speed_mps: Optional[float] = None
    predicted_speed_kmph: Optional[float] = None
    interval_lower_mps: Optional[float] = None
    interval_upper_mps: Optional[float] = None
    confidence_level: float = 0.90
    abstention_reason: Optional[AbstentionReason] = None
    is_abstained: bool
    data_mode: DataMode = DataMode.SYNTHETIC

    model_config = ConfigDict(from_attributes=True)
