"""Unit tests for the Static Scenario Routing and Recommendation Engine."""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap local packages into sys.path
_workspace = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

import pytest
from backend.app.database import SessionLocal
from backend.app.models import RoadSegment
from backend.app.schemas.common import SensitivityOutcome
from backend.app.schemas.simulation import ScenarioOverride
from backend.app.services.simulation import (
    NetworkGraphManager,
    calculate_edge_travel_time,
    evaluate_scenarios_and_recommend,
    find_optimal_route,
)
from pipelines.ingest.seed import seed_database


@pytest.fixture(scope="module")
def seeded_segments():
    session = SessionLocal()
    seed_database(session, reset=True)
    segments = session.query(RoadSegment).all()
    session.close()
    return segments


def test_baseline_route_calculation(seeded_segments):
    manager = NetworkGraphManager(seeded_segments)
    route = find_optimal_route(
        manager.baseline_graph,
        origin="node_origin",
        destination="node_destination",
    )
    assert route.is_reachable is True
    assert len(route.edge_ids) > 0
    assert route.nodes == ["node_origin", "node_corridor_mid", "node_destination"]
    # Total length: corridor_w (1150 or 1200) + corridor_e (1400)
    assert route.total_length_meters > 0
    assert route.estimated_travel_time_seconds > 0


def test_parallel_edges_preservation(seeded_segments):
    """Confirm express lane parallel edge is selected when it is faster."""
    manager = NetworkGraphManager(seeded_segments)
    route = find_optimal_route(
        manager.baseline_graph,
        origin="node_origin",
        destination="node_corridor_mid",
    )
    assert route.is_reachable is True
    # The express segment (1150m @ 16.67 m/s = 69s) is faster than local (1200m @ 13.89 m/s = 86.4s)
    assert "seg_corridor_w_express" in route.edge_ids


def test_one_way_street_traversal(seeded_segments):
    manager = NetworkGraphManager(seeded_segments)
    
    # Forward traversal South to North: ALLOWED
    forward = find_optimal_route(
        manager.baseline_graph,
        origin="node_corridor_mid",
        destination="node_hub_north",
    )
    assert forward.is_reachable is True
    assert forward.edge_ids == ["seg_oneway_north"]

    # Reverse traversal North to South: MUST BE UNREACHABLE
    reverse = find_optimal_route(
        manager.baseline_graph,
        origin="node_hub_north",
        destination="node_corridor_mid",
    )
    assert reverse.is_reachable is False


def test_full_closure_rerouting_to_bypass(seeded_segments):
    manager = NetworkGraphManager(seeded_segments)
    
    # Close both forward and reverse corridor east segments
    overrides = {
        "seg_corridor_e": ScenarioOverride(closed=True),
        "seg_corridor_e_rev": ScenarioOverride(closed=True),
    }
    scenario_g = manager.create_scenario_graph(overrides)

    route = find_optimal_route(
        scenario_g,
        origin="node_origin",
        destination="node_destination",
    )
    assert route.is_reachable is True
    # Corridor is closed -> Route must switch to bypass segments
    assert "seg_corridor_e" not in route.edge_ids
    assert "seg_bypass_w" in route.edge_ids
    assert "seg_bypass_e" in route.edge_ids


def test_disconnected_destination_handling(seeded_segments):
    manager = NetworkGraphManager(seeded_segments)
    route = find_optimal_route(
        manager.baseline_graph,
        origin="node_origin",
        destination="node_isolated",
    )
    assert route.is_reachable is False
    assert route.estimated_travel_time_seconds == float("inf")


def test_origin_equals_destination(seeded_segments):
    manager = NetworkGraphManager(seeded_segments)
    route = find_optimal_route(
        manager.baseline_graph,
        origin="node_origin",
        destination="node_origin",
    )
    assert route.is_reachable is True
    assert route.total_length_meters == 0.0
    assert route.estimated_travel_time_seconds == 0.0
    assert route.nodes == ["node_origin"]


def test_baseline_graph_immutability(seeded_segments):
    """Ensure running scenarios with overrides never mutates the underlying baseline graph."""
    manager = NetworkGraphManager(seeded_segments)
    baseline_edges_before = list(manager.baseline_graph.edges(keys=True, data=True))

    # Run heavy scenario closing roads
    overrides = {"seg_corridor_e": ScenarioOverride(closed=True)}
    _ = manager.create_scenario_graph(overrides)

    baseline_edges_after = list(manager.baseline_graph.edges(keys=True, data=True))
    assert len(baseline_edges_before) == len(baseline_edges_after)
    assert baseline_edges_before == baseline_edges_after


def test_invalid_speed_and_delay_rejected():
    with pytest.raises(ValueError):
        calculate_edge_travel_time({"length_meters": 1000.0, "free_flow_speed_mps": -5.0})

    with pytest.raises(ValueError):
        calculate_edge_travel_time({"length_meters": 1000.0, "free_flow_speed_mps": 15.0, "delay_seconds": -10.0})


def test_recommendation_evidence_sensitive_vs_robust(seeded_segments):
    """Verify recommendation sensitivity classification across different slowdown levels."""
    
    # 1. Mild/moderate slowdown (speed 11.8 m/s, delay 10s): Corridor is still faster than bypass -> EVIDENCE_SENSITIVE
    rec_moderate = evaluate_scenarios_and_recommend(
        seeded_segments,
        origin="node_origin",
        destination="node_destination",
        incident_segment_id="seg_corridor_e",
        slowdown_multiplier=0.85,
        slowdown_delay_seconds=10.0,
    )
    assert rec_moderate.recommendation.sensitivity_outcome == SensitivityOutcome.EVIDENCE_SENSITIVE
    assert "The preferred route changes between slowdown and closure scenarios" in rec_moderate.recommendation.explanation

    # 2. Extreme slowdown (speed 1.0 m/s, delay 400s): Bypass is clearly faster in slowdown AND closure -> ROBUST_ALTERNATIVE
    rec_extreme = evaluate_scenarios_and_recommend(
        seeded_segments,
        origin="node_origin",
        destination="node_destination",
        incident_segment_id="seg_corridor_e",
        slowdown_multiplier=0.10,
        slowdown_delay_seconds=500.0,
    )
    assert rec_extreme.recommendation.sensitivity_outcome == SensitivityOutcome.ROBUST_ALTERNATIVE
    assert "lower estimated travel cost across all tested assumptions" in rec_extreme.recommendation.explanation


def test_recommendation_insufficient_data(seeded_segments):
    """Verify recommendation when origin and destination are disconnected under baseline."""
    rec_isolated = evaluate_scenarios_and_recommend(
        seeded_segments,
        origin="node_origin",
        destination="node_isolated",
    )
    assert rec_isolated.recommendation.sensitivity_outcome == SensitivityOutcome.INSUFFICIENT_DATA
    assert "Available data is insufficient" in rec_isolated.recommendation.explanation


def test_recommendation_closure_severs_route(seeded_segments):
    """Verify recommendation when destination cannot be reached under closure."""
    rec_severed = evaluate_scenarios_and_recommend(
        seeded_segments,
        origin="node_origin",
        destination="node_hub_north",
        incident_segment_id="seg_oneway_north",
    )
    assert rec_severed.recommendation.sensitivity_outcome == SensitivityOutcome.NO_ROUTE_AVAILABLE
    assert "No traversable route exists under the full-closure scenario" in rec_severed.recommendation.explanation
