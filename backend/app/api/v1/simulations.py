"""Static scenario simulation and recommendation API endpoints."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.config import settings
from backend.app.models import Recommendation, RoadSegment, SimulationRun
from backend.app.schemas.common import SensitivityOutcome
from backend.app.schemas.simulation import (
    RecommendationResponse,
    RouteAlternative,
    ScenarioEvaluation,
    SimulationRequest,
    SimulationRunResponse,
)
from backend.app.services.simulation.recommendation import (
    DECISION_RULE_VERSION,
    evaluate_scenarios_and_recommend,
)
from backend.app.services.simulation.router import (
    NetworkGraphManager,
    find_optimal_route,
)

router = APIRouter(tags=["Scenario Simulations & Routing"])


@router.post(
    "/simulations",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run an isolated scenario simulation with custom overrides and persist run",
)
def create_simulation(
    body: SimulationRequest,
    db: Session = Depends(get_db),
) -> SimulationRunResponse:
    """Run an isolated scenario route search.

    Guarantees:
    - Never mutates the baseline network.
    - Preserves parallel edge identities and directed one-way streets.
    - Persists the simulation run in the database.
    """
    segments = db.query(RoadSegment).all()
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Road network has no registered segments. Please seed database first.",
        )

    now = datetime.now(timezone.utc)
    manager = NetworkGraphManager(segments)

    # Isolated scenario graph with user overrides applied
    scenario_graph = manager.create_scenario_graph(body.overrides)

    route_res = find_optimal_route(
        graph=scenario_graph,
        origin=body.origin_node,
        destination=body.destination_node,
        route_name="Scenario Optimal Route",
        assumptions="Custom user-specified scenario overrides",
    )

    run_id = f"sim_{uuid.uuid4().hex[:8]}"
    scenarios: Dict[str, ScenarioEvaluation] = {
        "custom": ScenarioEvaluation(
            scenario_type="custom",
            reference_route=route_res,
            candidate_routes=[route_res],
            preferred_route_name=route_res.route_name,
            time_saved_seconds=0.0,
        )
    }

    sim_run_response = SimulationRunResponse(
        id=run_id,
        created_at=now,
        baseline_snapshot_time=now,
        graph_version=settings.graph_version,
        scenario_type="custom",
        recommendation=None,
        scenarios=scenarios,
        sensitivity_summary="Isolated single scenario evaluation completed.",
    )

    # Persist simulation run in database
    db_run = SimulationRun(
        id=run_id,
        created_at=now,
        baseline_snapshot_time=now,
        graph_version=settings.graph_version,
        scenario_type="custom",
        overrides_json=json.dumps(
            {k: v.model_dump() for k, v in body.overrides.items()}
        ),
        route_results_json=json.dumps(
            {k: v.model_dump(mode="json") for k, v in scenarios.items()}
        ),
        algorithm_version="dijkstra_v1.0",
    )
    db.add(db_run)
    db.commit()

    return sim_run_response


@router.get(
    "/simulations/{id}",
    response_model=SimulationRunResponse,
    summary="Retrieve a previously executed and persisted simulation run by ID",
)
def get_simulation_run(
    id: str,
    db: Session = Depends(get_db),
) -> SimulationRunResponse:
    """Retrieve saved simulation run and recommendation results."""
    db_run = db.query(SimulationRun).filter(SimulationRun.id == id).first()
    if not db_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{id}' not found.",
        )

    # Reconstitute scenarios
    scenarios_dict: Dict[str, ScenarioEvaluation] = {}
    for name, data in db_run.route_results.items():
        try:
            scenarios_dict[name] = ScenarioEvaluation.model_validate(data)
        except Exception:
            pass

    # Reconstitute recommendation if present
    rec_response: RecommendationResponse | None = None
    if db_run.recommendation:
        rec_response = RecommendationResponse(
            id=db_run.recommendation.id,
            simulation_run_id=db_run.id,
            decision_rule_version=db_run.recommendation.decision_rule_version,
            explanation=db_run.recommendation.explanation,
            sensitivity_outcome=SensitivityOutcome(db_run.recommendation.sensitivity_outcome),
            minimum_benefit_seconds=db_run.recommendation.minimum_benefit_seconds,
            created_at=db_run.recommendation.created_at,
        )

    return SimulationRunResponse(
        id=db_run.id,
        created_at=db_run.created_at,
        baseline_snapshot_time=db_run.baseline_snapshot_time,
        graph_version=db_run.graph_version,
        scenario_type=db_run.scenario_type,
        recommendation=rec_response,
        scenarios=scenarios_dict,
        sensitivity_summary=rec_response.explanation if rec_response else "Saved scenario run.",
    )


@router.post(
    "/simulations/compare",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compare baseline, slowdown, and closure scenarios with assumption sensitivity analysis",
)
@router.post(
    "/simulation/recommend",
    response_model=SimulationRunResponse,
    include_in_schema=False,
)
def compare_scenarios_and_recommend(
    body: SimulationRequest,
    db: Session = Depends(get_db),
) -> SimulationRunResponse:
    """Run full assumption sensitivity analysis across baseline, slowdown, and closure.

    Signature Feature:
    - Tests whether candidate alternative routes remain faster across varied degrees of impairment.
    - Classifies routing outcome as:
      - ROBUST_ALTERNATIVE: Alternative is beneficial across all tested assumptions.
      - EVIDENCE_SENSITIVE: Preferred route flips between slowdown and closure; better evidence needed.
      - NO_ROUTE_AVAILABLE: Closure leaves destination disconnected.
      - INSUFFICIENT_DATA: Disconnected in baseline.
    - Baseline graph is guaranteed immutable.
    - Persists the comparison and recommendation in the database.
    """
    segments = db.query(RoadSegment).all()
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Road network has no registered segments. Please seed database first.",
        )

    # Run recommendation service
    run_response = evaluate_scenarios_and_recommend(
        segments=segments,
        origin=body.origin_node,
        destination=body.destination_node,
        incident_segment_id=body.incident_segment_id,
        minimum_benefit_seconds=body.minimum_benefit_seconds,
        graph_version=settings.graph_version,
    )

    # Persist in DB
    now = datetime.now(timezone.utc)
    db_run = SimulationRun(
        id=run_response.id,
        created_at=now,
        baseline_snapshot_time=run_response.baseline_snapshot_time,
        graph_version=settings.graph_version,
        scenario_type="baseline_vs_slowdown_vs_closure",
        overrides_json=json.dumps({k: v.model_dump() for k, v in body.overrides.items()}),
        route_results_json=json.dumps(
            {k: v.model_dump(mode="json") for k, v in run_response.scenarios.items()}
        ),
        algorithm_version="dijkstra_v1.0",
    )
    db.add(db_run)
    db.flush()

    if run_response.recommendation:
        db_rec = Recommendation(
            id=run_response.recommendation.id,
            simulation_run_id=db_run.id,
            decision_rule_version=DECISION_RULE_VERSION,
            explanation=run_response.recommendation.explanation,
            sensitivity_outcome=run_response.recommendation.sensitivity_outcome.value,
            minimum_benefit_seconds=body.minimum_benefit_seconds,
            created_at=now,
        )
        db.add(db_rec)

    db.commit()

    return run_response
