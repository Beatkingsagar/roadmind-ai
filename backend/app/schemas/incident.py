"""Incident episode and reviewer audit schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import ReviewDecision
from backend.app.schemas.report import ReportResponse


class IncidentReviewCreate(BaseModel):
    reviewer_reference: str
    decision: ReviewDecision
    reason: str = Field(min_length=3, max_length=1000)


class IncidentReviewResponse(BaseModel):
    id: str
    episode_id: str
    reviewer_reference: str
    decision: str
    reason: str
    previous_state: str
    recorded_at: datetime
    available_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentEpisodeResponse(BaseModel):
    id: str
    primary_segment_id: str
    affected_segments: List[str]
    episode_type: str
    first_reported_at: datetime
    last_reported_at: datetime
    lifecycle_status: str
    severity_level: str
    heuristic_support_score: float
    assessment_summary: str
    rubric_version: str
    reviewer_state: str
    report_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class IncidentEpisodeDetailResponse(IncidentEpisodeResponse):
    reports: List[ReportResponse] = []
    reviews: List[IncidentReviewResponse] = []
