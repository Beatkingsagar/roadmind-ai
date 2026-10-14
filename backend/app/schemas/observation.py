"""Observation schemas with explicit unit support."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import DataMode


class ObservationBase(BaseModel):
    segment_id: str
    observed_at: datetime
    available_at: datetime
    value: float = Field(ge=0, description="Observed speed")
    unit: str = "mps"
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: str = "synthetic_sensor"
    data_mode: DataMode = DataMode.SYNTHETIC


class ObservationCreate(ObservationBase):
    id: str


class ObservationResponse(ObservationBase):
    id: str
    speed_mps: float
    speed_kmph: float

    model_config = ConfigDict(from_attributes=True)
