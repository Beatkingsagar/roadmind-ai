"""Assumption-Sensitive Recommendation Engine for RoadMind AI.

Signature Feature:
Evaluates routing decisions across three explicit incident assumption scenarios:
1. Baseline (Reference free-flow)
2. Partial Slowdown
3. Full Closure

Compares candidate alternatives against the reference route and classifies sensitivity:
- ROBUST_ALTERNATIVE: Alternative is beneficial across all tested assumptions.
- EVIDENCE_SENSITIVE: Preferred route changes between slowdown and closure; confirming blockage is critical.
- NO_ROUTE_AVAILABLE: Destination unreachable under closure.
- INSUFFICIENT_DATA: Insufficient connectivity.

No scenario probabilities or artificial likelihoods are invented.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.models import RoadSegment
from backend.app.schemas.common import SensitivityOutcome
from backend.app.schemas.simulation import (
    RecommendationResponse,
    RouteAlternative,
    ScenarioEvaluation,
    ScenarioOverride,
    SimulationRunResponse,
)
from backend.app.services.simulation.router import (
    NetworkGraphManager,
    compute_fixed_route_travel_time,
    find_optimal_route,
)

DECISION_RULE_VERSION = "rule_v1.0"
ALGORITHM_VERSION = "dijkstra_v1.0"


def evaluate_scenarios_and_recommend(
    segments: List[RoadSegment],
    origin: str,
    destination: str,
    incident_segment_id: Optional[str] = None,
    slowdown_multiplier: float = 0.30,  # 70% speed drop on incident segment
    slowdown_delay_seconds: float = 90.0,
    minimum_benefit_seconds: float = 30.0,
    graph_version: str = "v1.0.0",
    baseline_snapshot_time: Optional[datetime] = None,
) -> SimulationRunResponse:
    """Run full assumption sensitivity analysis across baseline, slowdown, and closure."""
    now = datetime.now(timezone.utc)
    snapshot_time = baseline_snapshot_time or now
    manager = NetworkGraphManager(segments)

    # 1. Baseline Scenario
    baseline_graph = manager.baseline_graph
    baseline_route = find_optimal_route(
        baseline_graph, origin, destination,
        route_name="Reference Corridor Route",
        assumptions="Baseline Free-Flow (No Incident)",
    )

    scenarios: Dict[str, ScenarioEvaluation] = {}
    scenarios["baseline"] = ScenarioEvaluation(
        scenario_type="baseline",
        reference_route=baseline_route,
        candidate_routes=[baseline_route],
        preferred_route_name=baseline_route.route_name,
        time_saved_seconds=0.0,
    )

    # If origin and destination are disconnected even in baseline
    if not baseline_route.is_reachable:
        rec_id = f"rec_{uuid.uuid4().hex[:8]}"
        run_id = f"sim_{uuid.uuid4().hex[:8]}"
        recommendation = RecommendationResponse(
            id=rec_id,
            simulation_run_id=run_id,
            decision_rule_version=DECISION_RULE_VERSION,
            explanation="Available data is insufficient for this comparison. Origin and destination are disconnected.",
            sensitivity_outcome=SensitivityOutcome.INSUFFICIENT_DATA,
            minimum_benefit_seconds=minimum_benefit_seconds,
            created_at=now,
        )
        return SimulationRunResponse(
            id=run_id,
            created_at=now,
            baseline_snapshot_time=snapshot_time,
            graph_version=graph_version,
            scenario_type="baseline",
            recommendation=recommendation,
            scenarios=scenarios,
            sensitivity_summary="Available data is insufficient for this comparison.",
        )

    # 2. Slowdown Scenario
    slowdown_overrides = {}
    if incident_segment_id:
        target_seg = next((s for s in segments if s.id == incident_segment_id), None)
        if target_seg:
            reduced_speed = max(1.0, target_seg.free_flow_speed_mps * slowdown_multiplier)
            slowdown_overrides[incident_segment_id] = ScenarioOverride(
                closed=False,
                speed_mps=reduced_speed,
                delay_seconds=slowdown_delay_seconds,
            )

    slowdown_graph = manager.create_scenario_graph(slowdown_overrides)

    # Evaluate the REFERENCE corridor along its baseline edge sequence under slowdown conditions
    ref_len, ref_time, ref_reachable = compute_fixed_route_travel_time(
        slowdown_graph, baseline_route.edge_ids
    )
    slowdown_ref_route = RouteAlternative(
        route_name=baseline_route.route_name,
        edge_ids=baseline_route.edge_ids if ref_reachable else [],
        nodes=baseline_route.nodes if ref_reachable else [],
        total_length_meters=ref_len if ref_reachable else 0.0,
        estimated_travel_time_seconds=ref_time if ref_reachable else float("inf"),
        is_reachable=ref_reachable,
        assumptions_applied=f"Reference Corridor with slowdown on {incident_segment_id or 'incident segment'}",
    )

    # Check candidate alternative route (diverting around incident corridor)
    bypass_graph = manager.create_scenario_graph({incident_segment_id: ScenarioOverride(closed=True)} if incident_segment_id else {})
    bypass_route = find_optimal_route(
        bypass_graph, origin, destination,
        route_name="Alternative Bypass Route",
        assumptions="Alternative Diverting Route (incident corridor avoided)",
    )

    # Evaluate slowdown comparison
    preferred_slowdown = slowdown_ref_route
    time_saved_slowdown = 0.0
    if bypass_route.is_reachable:
        if not slowdown_ref_route.is_reachable or (bypass_route.estimated_travel_time_seconds + minimum_benefit_seconds < slowdown_ref_route.estimated_travel_time_seconds):
            preferred_slowdown = bypass_route
            time_saved_slowdown = (slowdown_ref_route.estimated_travel_time_seconds - bypass_route.estimated_travel_time_seconds) if slowdown_ref_route.is_reachable else 0.0

    candidate_slowdown = [slowdown_ref_route]
    if bypass_route.is_reachable and bypass_route.edge_ids != slowdown_ref_route.edge_ids:
        candidate_slowdown.append(bypass_route)

    scenarios["slowdown"] = ScenarioEvaluation(
        scenario_type="slowdown",
        reference_route=slowdown_ref_route,
        candidate_routes=candidate_slowdown,
        preferred_route_name=preferred_slowdown.route_name,
        time_saved_seconds=round(time_saved_slowdown, 1),
    )

    # 3. Closure Scenario
    closure_overrides = {incident_segment_id: ScenarioOverride(closed=True)} if incident_segment_id else {}
    closure_graph = manager.create_scenario_graph(closure_overrides)
    closure_route = find_optimal_route(
        closure_graph, origin, destination,
        route_name="Post-Closure Detour",
        assumptions=f"Full Closure of {incident_segment_id or 'corridor'}",
    )

    scenarios["closure"] = ScenarioEvaluation(
        scenario_type="closure",
        reference_route=None,  # Corridor is closed
        candidate_routes=[closure_route] if closure_route.is_reachable else [],
        preferred_route_name=closure_route.route_name if closure_route.is_reachable else None,
        time_saved_seconds=0.0,
    )

    # 4. Sensitivity Classification & Recommendation Formulation
    run_id = f"sim_{uuid.uuid4().hex[:8]}"
    rec_id = f"rec_{uuid.uuid4().hex[:8]}"

    if not closure_route.is_reachable:
        outcome = SensitivityOutcome.NO_ROUTE_AVAILABLE
        explanation = (
            f"No traversable route exists under the full-closure scenario. "
            f"Network connectivity to destination is severed if road is fully blocked."
        )
    elif preferred_slowdown.route_name == bypass_route.route_name:
        # Bypass is faster in BOTH slowdown and closure!
        outcome = SensitivityOutcome.ROBUST_ALTERNATIVE
        explanation = (
            f"This alternative has a lower estimated travel cost across all tested assumptions. "
            f"Saves ~{time_saved_slowdown:.0f}s under partial slowdown ({bypass_route.estimated_travel_time_seconds:.0f}s vs {slowdown_ref_route.estimated_travel_time_seconds:.0f}s) "
            f"and provides traversable access ({closure_route.estimated_travel_time_seconds:.0f}s) under total road closure."
        )
    else:
        # Reference corridor is still faster under slowdown, but alternative is required under closure!
        outcome = SensitivityOutcome.EVIDENCE_SENSITIVE
        diff = bypass_route.estimated_travel_time_seconds - slowdown_ref_route.estimated_travel_time_seconds
        explanation = (
            f"The preferred route changes between slowdown and closure scenarios. Confirming the blockage could change the decision. "
            f"Reference corridor remains faster under partial slowdown ({slowdown_ref_route.estimated_travel_time_seconds:.0f}s vs {bypass_route.estimated_travel_time_seconds:.0f}s, +{diff:.0f}s for bypass), "
            f"but alternative bypass ({closure_route.estimated_travel_time_seconds:.0f}s) is required if full closure occurs."
        )

    recommendation = RecommendationResponse(
        id=rec_id,
        simulation_run_id=run_id,
        decision_rule_version=DECISION_RULE_VERSION,
        explanation=explanation,
        sensitivity_outcome=outcome,
        minimum_benefit_seconds=minimum_benefit_seconds,
        created_at=now,
    )

    return SimulationRunResponse(
        id=run_id,
        created_at=now,
        baseline_snapshot_time=snapshot_time,
        graph_version=graph_version,
        scenario_type="multi_scenario_comparison",
        recommendation=recommendation,
        scenarios=scenarios,
        sensitivity_summary=explanation,
    )
