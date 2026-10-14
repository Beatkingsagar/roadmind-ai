"""Simulation and scenario routing schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import SensitivityOutcome


class ScenarioOverride(BaseModel):
    closed: bool = False
    speed_mps: Optional[float] = Field(default=None, gt=0)
    delay_seconds: float = Field(default=0.0, ge=0)


class SimulationRequest(BaseModel):
    origin_node: str
    destination_node: str
    incident_segment_id: Optional[str] = None
    overrides: Dict[str, ScenarioOverride] = Field(default_factory=dict)
    minimum_benefit_seconds: float = Field(default=30.0, ge=0)


class RouteAlternative(BaseModel):
    route_name: str
    edge_ids: List[str]
    nodes: List[str]
    total_length_meters: float
    estimated_travel_time_seconds: float
    is_reachable: bool = True
    assumptions_applied: str


class ScenarioEvaluation(BaseModel):
    scenario_type: str  # baseline, slowdown, closure
    reference_route: Optional[RouteAlternative] = None
    candidate_routes: List[RouteAlternative] = []
    preferred_route_name: Optional[str] = None
    time_saved_seconds: float = 0.0


class RecommendationResponse(BaseModel):
    id: str
    simulation_run_id: str
    decision_rule_version: str
    explanation: str
    sensitivity_outcome: SensitivityOutcome
    minimum_benefit_seconds: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationRunResponse(BaseModel):
    id: str
    created_at: datetime
    baseline_snapshot_time: datetime
    graph_version: str
    scenario_type: str
    recommendation: Optional[RecommendationResponse] = None
    scenarios: Dict[str, ScenarioEvaluation] = {}
    sensitivity_summary: str

    model_config = ConfigDict(from_attributes=True)
