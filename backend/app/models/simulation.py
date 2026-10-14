"""Simulation run and recommendation models for static scenario comparison."""

from __future__ import annotations

import json
from typing import Any, Dict
from sqlalchemy import Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String(64), primary_key=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    baseline_snapshot_time = Column(UTCDateTime, nullable=False)
    graph_version = Column(String(32), default="v1.0.0", nullable=False)
    scenario_type = Column(String(32), nullable=False)  # baseline, slowdown, closure
    
    # Overrides applied to scenario graph (isolated from real baseline)
    overrides_json = Column(Text, default="{}", nullable=False)
    
    # Route comparison results (geometry, distances, costs in seconds, edge IDs)
    route_results_json = Column(Text, default="{}", nullable=False)
    algorithm_version = Column(String(32), default="dijkstra_v1.0", nullable=False)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="simulation_run", uselist=False, cascade="all, delete-orphan")

    @property
    def overrides(self) -> Dict[str, Any]:
        try:
            return json.loads(self.overrides_json)
        except Exception:
            return {}

    @property
    def route_results(self) -> Dict[str, Any]:
        try:
            return json.loads(self.route_results_json)
        except Exception:
            return {}

    def __repr__(self) -> str:
        return f"<SimulationRun id={self.id} scenario={self.scenario_type} algo={self.algorithm_version}>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(64), primary_key=True)
    simulation_run_id = Column(String(64), ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    decision_rule_version = Column(String(32), default="rule_v1.0", nullable=False)
    explanation = Column(Text, nullable=False)
    
    # Categorical sensitivity result
    # ROBUST_ALTERNATIVE: Alternate route is faster across all tested assumptions (slowdown and closure)
    # EVIDENCE_SENSITIVE: Preferred route changes depending on blockage vs slowdown (better evidence needed)
    # NO_ROUTE_AVAILABLE: Closure leaves destination unreachable
    # INSUFFICIENT_DATA: Sparse observations prevent reliable cost estimation
    sensitivity_outcome = Column(String(32), nullable=False)
    minimum_benefit_seconds = Column(Float, default=30.0, nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="recommendation")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} outcome={self.sensitivity_outcome}>"
