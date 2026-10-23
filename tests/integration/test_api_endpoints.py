"""Integration tests for RoadMind AI FastAPI Backend.

Covers all 13 acceptance criteria from Phase 3:
1. Health endpoint and application startup.
2. Network and road-state retrieval.
3. Report validation and persistence.
4. Idempotent report creation and conflicting idempotency keys.
5. Evidence hashing and duplicate detection.
6. Review authorization boundaries.
7. Temporal replay and future-record exclusion.
8. Forecast and evaluation retrieval.
9. Simulation creation, retrieval, and comparison.
10. Baseline network immutability.
11. Road history and memory-priority endpoints.
12. Invalid identifiers, malformed payloads, and HTTP status codes.
13. Database persistence across application restart.
"""

from __future__ import annotations

import io
import json
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
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import IncidentEpisode, Report, RoadSegment, SimulationRun
from pipelines.ingest.seed import seed_database


@pytest.fixture(scope="module")
def test_db_path():
    """Workspace-local SQLite database file for integration testing."""
    db_file = Path(__file__).resolve().parent / "test_roadmind.db"
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass
    yield db_file
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


@pytest.fixture(scope="module")
def test_db_engine(test_db_path):
    """SQLAlchemy engine bound to the temporary database file with foreign keys."""
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def seeded_client(test_db_engine):
    """FastAPI TestClient with seeded deterministic fixtures and overridden DB dependency."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine, future=True)

    # Seed the test database
    seed_session = TestingSessionLocal()
    seed_database(seed_session, reset=True)
    seed_session.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ==============================================================================
# 1. Health Endpoint and Application Startup
# ==============================================================================
def test_health_endpoint_and_startup(seeded_client):
    """Verify /api/health returns healthy status and metadata."""
    response = seeded_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert data["app_name"] == "RoadMind AI"


# ==============================================================================
# 2. Network and Road-State Retrieval
# ==============================================================================
def test_network_geojson_retrieval(seeded_client):
    """Verify GET /api/v1/network returns a complete GeoJSON FeatureCollection."""
    response = seeded_client.get("/api/v1/network")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

    first_feat = data["features"][0]
    assert first_feat["type"] == "Feature"
    assert "geometry" in first_feat
    assert first_feat["geometry"]["type"] == "LineString"
    assert "properties" in first_feat
    assert "free_flow_speed_mps" in first_feat["properties"]


def test_road_state_retrieval_with_replay(seeded_client):
    """Verify GET /api/v1/road-state returns segment snapshots as of replay cutoff."""
    replay_cutoff = "2026-10-15T08:30:00Z"
    response = seeded_client.get(f"/api/v1/road-state?at={replay_cutoff}")
    assert response.status_code == 200
    snapshots = response.json()
    assert isinstance(snapshots, list)
    assert len(snapshots) > 0

    seg_ids = [s["segment_id"] for s in snapshots]
    assert "seg_corridor_w" in seg_ids
    assert "seg_corridor_e" in seg_ids

    # Find the corridor segment with known active incident
    corridor_e = next(s for s in snapshots if s["segment_id"] == "seg_corridor_e")
    assert corridor_e["active_incidents_count"] >= 1
    assert corridor_e["congestion_ratio"] > 0


# ==============================================================================
# 3. Report Validation and Persistence
# ==============================================================================
def test_report_creation_and_persistence(seeded_client):
    """Verify POST /api/v1/reports validates and persists a new citizen report."""
    payload = {
        "incident_type": "accident",
        "claimed_event_time": "2026-10-15T09:00:00Z",
        "segment_id": "seg_corridor_w",
        "location_description": "Near Mile Marker 4, Grand Corridor West",
        "latitude": 40.7485,
        "longitude": -73.9840,
        "reporter_reference": "citizen_witness_101",
        "dependency_group_id": "dep_group_alpha",
        "description": "Multi-car rear-end collision blocking the right lane.",
        "idempotency_key": "idemp_test_report_unique_01",
    }
    response = seeded_client.post("/api/v1/reports", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("rep_")
    assert data["incident_type"] == "accident"
    assert data["segment_id"] == "seg_corridor_w"
    assert data["episode_id"] is not None


# ==============================================================================
# 4. Idempotent Report Creation & Conflicting Idempotency Keys
# ==============================================================================
def test_idempotent_report_creation(seeded_client):
    """Submitting the exact same idempotency key and payload returns the identical report."""
    key = "idemp_key_reuse_deterministic_02"
    payload = {
        "incident_type": "pothole",
        "claimed_event_time": "2026-10-15T09:15:00Z",
        "segment_id": "seg_corridor_w",
        "location_description": "Northbound lane 1, large depression",
        "latitude": 40.7489,
        "longitude": -73.9835,
        "reporter_reference": "citizen_404",
        "description": "Deep asphalt pothole near drainage grate.",
        "idempotency_key": key,
    }

    # First submission
    resp1 = seeded_client.post("/api/v1/reports", json=payload)
    assert resp1.status_code == 201
    rep1_id = resp1.json()["id"]

    # Second submission with identical payload
    resp2 = seeded_client.post("/api/v1/reports", json=payload)
    assert resp2.status_code in (200, 201)
    rep2_id = resp2.json()["id"]
    assert rep1_id == rep2_id


def test_conflicting_idempotency_key_rejected(seeded_client):
    """Reusing an idempotency key with different data returns HTTP 409 Conflict."""
    key = "idemp_key_conflict_03"
    payload_original = {
        "incident_type": "debris",
        "claimed_event_time": "2026-10-15T09:30:00Z",
        "segment_id": "seg_corridor_w",
        "location_description": "Center lane",
        "latitude": 40.7490,
        "longitude": -73.9830,
        "description": "Lost cargo crate on highway.",
        "idempotency_key": key,
    }
    resp1 = seeded_client.post("/api/v1/reports", json=payload_original)
    assert resp1.status_code == 201

    payload_conflicting = {
        **payload_original,
        "description": "DIFFERENT PAYLOAD: Overturned gravel truck across all lanes.",
    }
    resp2 = seeded_client.post("/api/v1/reports", json=payload_conflicting)
    assert resp2.status_code == 409
    assert "conflict" in resp2.json()["error"]["message"].lower()


# ==============================================================================
# 5. Evidence Hashing and Duplicate Detection
# ==============================================================================
def test_evidence_server_side_hashing_and_duplicate_detection(seeded_client):
    """Server computes SHA-256 and detects exact duplicate media uploads."""
    # First, submit a report to attach evidence to
    rep_resp = seeded_client.post(
        "/api/v1/reports",
        json={
            "incident_type": "accident",
            "claimed_event_time": "2026-10-15T09:40:00Z",
            "segment_id": "seg_corridor_w",
            "location_description": "Mile Marker 5",
            "latitude": 40.7495,
            "longitude": -73.9825,
            "description": "Incident for testing evidence hashing.",
        },
    )
    report_id = rep_resp.json()["id"]

    # Upload original media bytes
    sample_image_bytes = b"EXIF_IMAGE_TEST_MEDIA_BYTES_FOR_ROADMIND_2026"
    files = {"file": ("crash_scene.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")}
    data = {"metadata_claims": json.dumps({"camera_model": "PhoneCam_V1"})}

    resp_ev1 = seeded_client.post(f"/api/v1/reports/{report_id}/evidence", files=files, data=data)
    assert resp_ev1.status_code == 201
    ev1_data = resp_ev1.json()
    assert ev1_data["is_duplicate"] is False
    assert ev1_data["duplicate_of_id"] is None
    original_hash = ev1_data["content_hash"]
    ev1_id = ev1_data["id"]

    # Upload exact duplicate media bytes to the same or another report
    files_dup = {"file": ("crash_scene_copy.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")}
    resp_ev2 = seeded_client.post(f"/api/v1/reports/{report_id}/evidence", files=files_dup)
    assert resp_ev2.status_code == 201
    ev2_data = resp_ev2.json()
    assert ev2_data["is_duplicate"] is True
    assert ev2_data["duplicate_of_id"] == ev1_id
    assert ev2_data["content_hash"] == original_hash


def test_evidence_unsupported_format_and_oversized_rejection(seeded_client):
    """Verify that unsupported media extensions and oversized files (>10MB) are rejected."""
    # 1. Create a parent report
    rep_resp = seeded_client.post(
        "/api/v1/reports",
        json={
            "incident_type": "debris",
            "claimed_event_time": "2026-10-15T09:45:00Z",
            "segment_id": "seg_corridor_w",
            "location_description": "Near Mile Marker 2",
            "latitude": 40.7495,
            "longitude": -73.9825,
            "description": "Debris report for file validation testing.",
        },
    )
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # 2. Reject unsupported executable/binary file
    malicious_files = {"file": ("exploit.exe", io.BytesIO(b"MZtestexecutable"), "application/x-msdownload")}
    resp_unsupported = seeded_client.post(f"/api/v1/reports/{report_id}/evidence", files=malicious_files)
    assert resp_unsupported.status_code == 415
    assert "Unsupported media format" in resp_unsupported.json()["error"]["message"]

    # 3. Reject oversized file (>10MB)
    large_payload = b"X" * (11 * 1024 * 1024)
    oversized_files = {"file": ("gigantic_photo.jpg", io.BytesIO(large_payload), "image/jpeg")}
    resp_oversized = seeded_client.post(f"/api/v1/reports/{report_id}/evidence", files=oversized_files)
    assert resp_oversized.status_code == 413
    assert "exceeds maximum allowed size" in resp_oversized.json()["error"]["message"]



# ==============================================================================
# 6. Review Authorization Boundaries
# ==============================================================================
def test_review_authorization_boundary(seeded_client):
    """Only authorized traffic operators can submit reviews; unauthenticated requests receive 403."""
    # Get active episode
    incidents_resp = seeded_client.get("/api/v1/incidents")
    episodes = incidents_resp.json()
    assert len(episodes) > 0
    ep_id = episodes[0]["id"]

    review_payload = {
        "reviewer_reference": "traffic_officer_42",
        "decision": "verified",
        "reason": "Confirmed via TMC CCTV stream #14.",
    }

    # Unauthenticated request (no operator header or token)
    unauth_resp = seeded_client.post(f"/api/v1/incidents/{ep_id}/reviews", json=review_payload)
    assert unauth_resp.status_code == 403
    assert "authorization required" in unauth_resp.json()["error"]["message"].lower()

    # Invalid token
    bad_token_resp = seeded_client.post(
        f"/api/v1/incidents/{ep_id}/reviews",
        json=review_payload,
        headers={"X-Reviewer-Token": "invalid_wrong_secret"},
    )
    assert bad_token_resp.status_code == 403

    # Authorized request with X-Reviewer-Role header
    auth_resp = seeded_client.post(
        f"/api/v1/incidents/{ep_id}/reviews",
        json=review_payload,
        headers={"X-Reviewer-Role": "traffic_operator"},
    )
    assert auth_resp.status_code == 201
    review_data = auth_resp.json()
    assert review_data["decision"] == "verified"
    assert review_data["episode_id"] == ep_id

    # Verify episode's reviewer_state updated
    ep_detail_resp = seeded_client.get(f"/api/v1/incidents/{ep_id}")
    assert ep_detail_resp.status_code == 200
    assert ep_detail_resp.json()["reviewer_state"] == "verified"


# ==============================================================================
# 7. Temporal Replay and Future-Record Exclusion
# ==============================================================================
def test_temporal_replay_excludes_future_records(seeded_client):
    """Records available after replay timestamp T must NOT leak into responses."""
    # Replay time set to morning: 2026-10-15T08:00:00Z
    # In fixture, accident ep_corridor_accident_01 was first reported at 08:18:00Z
    early_replay = "2026-10-15T08:00:00Z"
    resp_early = seeded_client.get(f"/api/v1/incidents?at={early_replay}")
    assert resp_early.status_code == 200
    early_ep_ids = [ep["id"] for ep in resp_early.json()]
    assert "ep_corridor_accident_01" not in early_ep_ids

    # After incident occurs: 2026-10-15T08:30:00Z
    late_replay = "2026-10-15T08:30:00Z"
    resp_late = seeded_client.get(f"/api/v1/incidents?at={late_replay}")
    assert resp_late.status_code == 200
    late_ep_ids = [ep["id"] for ep in resp_late.json()]
    assert "ep_corridor_accident_01" in late_ep_ids


# ==============================================================================
# 8. Forecast and Evaluation Retrieval
# ==============================================================================
def test_forecasting_persistence_and_abstention(seeded_client):
    """Forecast returns predicted speed when observations exist, and abstains when sparse or stale."""
    # Active observations exist up to 08:30 on seg_corridor_e
    resp_forecast = seeded_client.get(
        "/api/v1/forecasts?segment_id=seg_corridor_e&at=2026-10-15T08:30:00Z&horizon_minutes=15&model_type=persistence"
    )
    assert resp_forecast.status_code == 200
    forecast_data = resp_forecast.json()
    assert forecast_data["is_abstained"] is False
    assert forecast_data["predicted_speed_mps"] is not None

    # Sparse / unobserved segment test (seg_sparse_history has sparse/no fresh observations)
    resp_sparse = seeded_client.get(
        "/api/v1/forecasts?segment_id=seg_sparse_history&at=2026-10-15T08:30:00Z&horizon_minutes=15&model_type=persistence"
    )
    assert resp_sparse.status_code == 200
    sparse_data = resp_sparse.json()
    assert sparse_data["is_abstained"] is True
    assert sparse_data["abstention_reason"] in ("UNOBSERVED_SEGMENT", "STALE_OBSERVATIONS", "INSUFFICIENT_HISTORY")


def test_evaluations_retrieval(seeded_client):
    """GET /api/v1/evaluations chronologically scores predictions against eligible actuals."""
    resp = seeded_client.get("/api/v1/evaluations?at=2026-10-15T08:30:00Z")
    assert resp.status_code == 200
    eval_data = resp.json()
    assert "sample_metrics" in eval_data
    assert "horizon_summaries" in eval_data


# ==============================================================================
# 9. Simulation Creation, Retrieval, and Comparison
# ==============================================================================
def test_simulation_run_lifecycle_and_comparison(seeded_client):
    """Tests POST /api/v1/simulations, GET /api/v1/simulations/{id}, and POST /api/v1/simulations/compare."""
    # 1. Create a custom simulation run
    sim_payload = {
        "origin_node": "node_origin",
        "destination_node": "node_destination",
        "overrides": {
            "seg_corridor_w": {
                "closed": False,
                "speed_mps": 5.0,
                "delay_seconds": 30.0,
            }
        },
    }
    create_resp = seeded_client.post("/api/v1/simulations", json=sim_payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    sim_id = run_data["id"]
    assert "custom" in run_data["scenarios"]

    # 2. Retrieve simulation run by ID from DB
    get_resp = seeded_client.get(f"/api/v1/simulations/{sim_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sim_id

    # 3. Run comparison across baseline, slowdown, and closure
    compare_payload = {
        "origin_node": "node_origin",
        "destination_node": "node_destination",
        "incident_segment_id": "seg_corridor_e",
        "minimum_benefit_seconds": 30.0,
    }
    compare_resp = seeded_client.post("/api/v1/simulations/compare", json=compare_payload)
    assert compare_resp.status_code == 201
    comp_data = compare_resp.json()
    assert "baseline" in comp_data["scenarios"]
    assert "slowdown" in comp_data["scenarios"]
    assert "closure" in comp_data["scenarios"]
    assert comp_data["recommendation"] is not None
    assert comp_data["recommendation"]["sensitivity_outcome"] in (
        "ROBUST_ALTERNATIVE",
        "EVIDENCE_SENSITIVE",
        "NO_ROUTE_AVAILABLE",
        "INSUFFICIENT_DATA",
    )


# ==============================================================================
# 10. Baseline Network Immutability
# ==============================================================================
def test_baseline_network_immutability(seeded_client):
    """Verify that running simulations with severe overrides never mutates baseline segments."""
    # Retrieve segment properties before simulation
    before_resp = seeded_client.get("/api/v1/network/segments")
    segments_before = {s["id"]: s for s in before_resp.json()}
    orig_speed = segments_before["seg_corridor_e"]["free_flow_speed_mps"]

    # Run comparison that closes seg_corridor_e
    seeded_client.post(
        "/api/v1/simulations/compare",
        json={
            "origin_node": "node_origin",
            "destination_node": "node_destination",
            "incident_segment_id": "seg_corridor_e",
        },
    )

    # Check segment properties after simulation: must be completely unchanged
    after_resp = seeded_client.get("/api/v1/network/segments")
    segments_after = {s["id"]: s for s in after_resp.json()}
    assert segments_after["seg_corridor_e"]["free_flow_speed_mps"] == orig_speed


# ==============================================================================
# 11. Road History and Memory-Priority Endpoints
# ==============================================================================
def test_segment_history_and_memory_priority(seeded_client):
    """Verify segment history retrieval and transparent memory inspection priorities."""
    # Segment history on segment with observations
    hist_resp = seeded_client.get("/api/v1/segments/seg_corridor_e/history?at=2026-10-15T08:30:00Z")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert "segment" in hist_data
    assert "memory_summary" in hist_data
    assert hist_data["total_observations_eligible"] >= 1

    # Memory priority ranking
    prio_resp = seeded_client.get("/api/v1/memory/priority?at=2026-10-15T08:30:00Z")
    assert prio_resp.status_code == 200
    priorities = prio_resp.json()
    assert isinstance(priorities, list)
    assert len(priorities) > 0

    first_prio = priorities[0]
    assert 0.0 <= first_prio["priority_score"] <= 100.0
    assert first_prio["priority_rank"] == 1
    assert "scoring_rubric_version" in first_prio
    assert "explanation" in first_prio


# ==============================================================================
# 12. Error Handling and Status Codes
# ==============================================================================
def test_error_handling_and_status_codes(seeded_client):
    """Verify standard error responses for invalid inputs, missing resources, and malformed queries."""
    # 404 for non-existent segment in report
    resp_404_seg = seeded_client.post(
        "/api/v1/reports",
        json={
            "incident_type": "accident",
            "claimed_event_time": "2026-10-15T09:00:00Z",
            "segment_id": "non_existent_segment_xyz",
            "location_description": "Nowhere",
            "latitude": 40.0,
            "longitude": -73.0,
            "description": "Ghost road report.",
        },
    )
    assert resp_404_seg.status_code == 404
    assert resp_404_seg.json()["status"] == "error"

    # 404 for non-existent incident episode detail
    resp_404_inc = seeded_client.get("/api/v1/incidents/ep_does_not_exist_999")
    assert resp_404_inc.status_code == 404

    # 404 for non-existent simulation run
    resp_404_sim = seeded_client.get("/api/v1/simulations/sim_non_existent_999")
    assert resp_404_sim.status_code == 404

    # 422 for malformed latitude (out of bounds > 90)
    resp_422 = seeded_client.post(
        "/api/v1/reports",
        json={
            "incident_type": "accident",
            "claimed_event_time": "2026-10-15T09:00:00Z",
            "segment_id": "seg_corridor_w",
            "location_description": "North Pole",
            "latitude": 999.0,  # Invalid
            "longitude": -73.0,
            "description": "Invalid coordinates.",
        },
    )
    assert resp_422.status_code == 422
    assert resp_422.json()["error"]["code"] == "VALIDATION_ERROR"

    # 400 for invalid timestamp format in 'at'
    resp_bad_time = seeded_client.get("/api/v1/road-state?at=not-a-timestamp")
    assert resp_bad_time.status_code == 400


# ==============================================================================
# 13. Persistence Across Application / Session Restart
# ==============================================================================
def test_persistence_across_application_restart(test_db_engine):
    """Verify that data written to SQLite persists when a new application instance connects."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine, future=True)

    # 1. Create a record using Session 1
    session1 = TestingSessionLocal()
    unique_run_id = "sim_persisted_across_restart_test_99"
    run_record = SimulationRun(
        id=unique_run_id,
        created_at=datetime.now(timezone.utc),
        baseline_snapshot_time=datetime.now(timezone.utc),
        graph_version="v1.0.0",
        scenario_type="restart_test",
        overrides_json="{}",
        route_results_json=json.dumps({"test": {"route_name": "Restart Verification Route"}}),
        algorithm_version="dijkstra_v1.0",
    )
    session1.add(run_record)
    session1.commit()
    session1.close()

    # 2. Re-instantiate application test client on the exact same database engine
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client2:
        resp = client2.get(f"/api/v1/simulations/{unique_run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == unique_run_id
        assert data["scenario_type"] == "restart_test"

    app.dependency_overrides.clear()

