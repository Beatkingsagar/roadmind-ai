"""Incident report submission and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import DataMode, IncidentType
from backend.app.schemas.evidence import EvidenceResponse


class ReportCreate(BaseModel):
    incident_type: IncidentType
    claimed_event_time: datetime
    segment_id: str
    location_description: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    reporter_reference: str = "anonymous_citizen"
    dependency_group_id: Optional[str] = None
    description: str = Field(min_length=3, max_length=2000)
    idempotency_key: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    incident_type: str
    claimed_event_time: datetime
    submitted_at: datetime
    available_at: datetime
    segment_id: str
    location_description: str
    latitude: float
    longitude: float
    reporter_reference: str
    dependency_group_id: Optional[str] = None
    description: str
    data_mode: DataMode
    idempotency_key: Optional[str] = None
    episode_id: Optional[str] = None
    evidence_items: List[EvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)
