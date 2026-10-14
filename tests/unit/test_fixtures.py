"""Unit tests verifying all 12 non-negotiable benchmark fixtures in the seeded database."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
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
from backend.app.models import (
    DataSource,
    Evidence,
    IncidentEpisode,
    Observation,
    OutcomeEvaluation,
    Prediction,
    Report,
    RoadSegment,
)
from pipelines.ingest.seed import seed_database


@pytest.fixture(scope="module")
def seeded_db():
    session = SessionLocal()
    seed_database(session, reset=True)
    try:
        yield session
    finally:
        session.close()


def test_fixture_1_one_way_road(seeded_db):
    """1. One-way road test fixture."""
    oneway = seeded_db.query(RoadSegment).filter_by(id="seg_oneway_north").first()
    assert oneway is not None
    assert oneway.is_one_way is True
    assert oneway.source_node == "node_corridor_mid"
    assert oneway.target_node == "node_hub_north"
    
    # Confirm no reverse segment exists from hub_north to corridor_mid
    reverse = (
        seeded_db.query(RoadSegment)
        .filter_by(source_node="node_hub_north", target_node="node_corridor_mid")
        .first()
    )
    assert reverse is None


def test_fixture_2_parallel_directed_edges(seeded_db):
    """2. Parallel directed edges preserving multi-edge identity."""
    local_edge = seeded_db.query(RoadSegment).filter_by(id="seg_corridor_w").first()
    express_edge = seeded_db.query(RoadSegment).filter_by(id="seg_corridor_w_express").first()

    assert local_edge is not None
    assert express_edge is not None
    assert local_edge.source_node == express_edge.source_node == "node_origin"
    assert local_edge.target_node == express_edge.target_node == "node_corridor_mid"
    assert local_edge.directed_edge_id != express_edge.directed_edge_id
    assert express_edge.directed_edge_id == "edge_express_1"


def test_fixture_3_corridor_and_bypass(seeded_db):
    """3. Corridor and Bypass routes exist and connect origin to destination."""
    corridor_edges = (
        seeded_db.query(RoadSegment)
        .filter(RoadSegment.id.in_(["seg_corridor_w", "seg_corridor_e"]))
        .all()
    )
    bypass_edges = (
        seeded_db.query(RoadSegment)
        .filter(RoadSegment.id.in_(["seg_bypass_w", "seg_bypass_e"]))
        .all()
    )
    assert len(corridor_edges) == 2
    assert len(bypass_edges) == 2


def test_fixture_4_disconnected_destination(seeded_db):
    """4. Disconnected destination handling: node_isolated has zero incoming edges."""
    incoming_to_isolated = (
        seeded_db.query(RoadSegment)
        .filter_by(target_node="node_isolated")
        .all()
    )
    assert len(incoming_to_isolated) == 0


def test_fixture_5_duplicate_uploaded_evidence(seeded_db):
    """5. Duplicate uploaded evidence links to original and does NOT add independent support."""
    ev_orig = seeded_db.query(Evidence).filter_by(id="ev_accident_orig_01").first()
    ev_dup = seeded_db.query(Evidence).filter_by(id="ev_accident_dup_02").first()

    assert ev_orig is not None
    assert ev_dup is not None
    assert ev_orig.content_hash == ev_dup.content_hash
    assert ev_orig.is_duplicate is False
    assert ev_dup.is_duplicate is True
    assert ev_dup.duplicate_of_id == ev_orig.id


def test_fixture_6_shared_source_reports(seeded_db):
    """6. Shared-source reports grouped under dependency group to cap contribution."""
    rep_1 = seeded_db.query(Report).filter_by(id="rep_accident_01").first()
    rep_2 = seeded_db.query(Report).filter_by(id="rep_accident_02_dup").first()

    assert rep_1.dependency_group_id is not None
    assert rep_1.dependency_group_id == rep_2.dependency_group_id == "dep_patrol_fleet_A"


def test_fixture_7_conflicting_evidence(seeded_db):
    """7. Conflicting evidence: claimed event in the future relative to submission."""
    rep_conflict = seeded_db.query(Report).filter_by(id="rep_conflict_01").first()
    assert rep_conflict is not None
    assert rep_conflict.claimed_event_time > rep_conflict.submitted_at


def test_fixture_8_distinct_recurring_episodes(seeded_db):
    """8. Distinct recurring episodes on the same segment without clumping as one failure."""
    ep_sep = seeded_db.query(IncidentEpisode).filter_by(id="ep_pothole_sep_resolved").first()
    ep_oct = seeded_db.query(IncidentEpisode).filter_by(id="ep_pothole_oct_active").first()

    assert ep_sep is not None and ep_oct is not None
    assert ep_sep.primary_segment_id == ep_oct.primary_segment_id == "seg_corridor_w"
    assert ep_sep.lifecycle_status == "resolved"
    assert ep_oct.lifecycle_status == "reported"
    assert ep_oct.first_reported_at > ep_sep.last_reported_at


def test_fixture_9_late_arriving_observation(seeded_db):
    """9. Late-arriving observation has available_at significantly later than observed_at."""
    obs_late = seeded_db.query(Observation).filter_by(id="obs_late_arriving_01").first()
    assert obs_late is not None
    delta = obs_late.available_at - obs_late.observed_at
    assert delta.total_seconds() >= 1800  # 30 minutes latency


def test_fixture_10_sparse_forecasting_history(seeded_db):
    """10. Sparse history road has an explicit abstention prediction record."""
    pred_sparse = seeded_db.query(Prediction).filter_by(id="pred_sparse_hist_30m").first()
    assert pred_sparse is not None
    assert pred_sparse.is_abstained is True
    assert pred_sparse.abstention_reason == "INSUFFICIENT_HISTORY"


def test_fixture_11_later_outcome_observation(seeded_db):
    """11. Later outcome observation exists at the exact target time of a prediction."""
    pred = seeded_db.query(Prediction).filter_by(id="pred_corridor_e_30m").first()
    obs_outcome = seeded_db.query(Observation).filter_by(id="obs_outcome_corridor_e_0900").first()

    assert pred is not None and obs_outcome is not None
    assert pred.target_time == obs_outcome.observed_at


def test_fixture_12_immutable_outcome_evaluation(seeded_db):
    """12. Evaluation compares prediction and actual observation without modifying prediction."""
    evaluation = seeded_db.query(OutcomeEvaluation).filter_by(id="eval_pred_corridor_e_30m").first()
    assert evaluation is not None
    assert evaluation.prediction_id == "pred_corridor_e_30m"
    assert evaluation.observation_id == "obs_outcome_corridor_e_0900"
    assert evaluation.absolute_error_mps == 0.4
    assert evaluation.within_interval is True
