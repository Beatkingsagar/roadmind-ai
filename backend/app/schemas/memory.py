"""Schemas for Road Memory and Inspection Priority Ranking."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ObservationCoverage(BaseModel):
    segment_id: str
    observation_count: int
    first_observation_time: Optional[datetime] = None
    latest_observation_time: Optional[datetime] = None
    coverage_span_hours: float = 0.0
    is_coverage_poor: bool = False
    coverage_limitation_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EpisodeCluster(BaseModel):
    id: str
    segment_id: str
    episode_type: str
    first_reported_at: datetime
    last_reported_at: datetime
    duration_minutes: float
    severity_level: str
    report_count: int
    report_ids: List[str]
    unique_source_count: int
    dependency_group_ids: List[str]

    model_config = ConfigDict(from_attributes=True)


class SegmentMemorySummary(BaseModel):
    segment_id: str
    segment_name: str
    observed_recurrence_count: int = Field(
        ...,
        description="Number of distinct spatiotemporal incident episodes. Without vehicle exposure, reported/observed recurrence is used, not per-vehicle risk."
    )
    total_report_count: int = Field(..., description="Raw total reports received.")
    duplicate_or_shared_reports_count: int = Field(
        ...,
        description="Reports grouped into existing episodes or shared-source groups."
    )
    average_episode_duration_minutes: float
    max_severity: str
    episodes: List[EpisodeCluster]
    observation_coverage: ObservationCoverage

    model_config = ConfigDict(from_attributes=True)


class InspectionPriority(BaseModel):
    segment_id: str
    segment_name: str
    priority_score: float = Field(..., ge=0.0, le=100.0, description="Transparent 0-100 inspection priority score.")
    priority_rank: int = Field(..., ge=1, description="1-based relative priority rank.")
    observed_recurrence_score: float
    severity_score: float
    duration_score: float
    coverage_uncertainty_score: float
    scoring_rubric_version: str = "inspection_v1.0"
    explanation: str
    data_limitations: List[str] = []

    model_config = ConfigDict(from_attributes=True)
