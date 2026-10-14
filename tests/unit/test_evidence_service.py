"""Unit tests for the Evidence Assessment Engine."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Bootstrap local packages into sys.path
_workspace = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models import Base, Evidence, Observation, Report, RoadSegment
from backend.app.services.evidence import (
    assess_evidence_for_reports,
    compute_evidence_hash,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Create road segment
        seg = RoadSegment(
            id="seg_evidence_test",
            name="Evidence Test Corridor",
            source_node="node_A",
            target_node="node_B",
            directed_edge_id="edge_0",
            length_meters=1000.0,
            free_flow_speed_mps=15.0,  # 54 km/h
            geometry_json="[]",
        )
        session.add(seg)
        session.commit()
        yield session
    finally:
        session.close()


def test_sha256_hash_computation():
    payload = b"IMAGE_BINARY_TEST_PAYLOAD"
    h1 = compute_evidence_hash(payload)
    h2 = compute_evidence_hash(payload)
    assert h1 == h2
    assert len(h1) == 64


def test_duplicate_evidence_does_not_increase_independent_support(test_db):
    t0 = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)
    seg = test_db.query(RoadSegment).filter_by(id="seg_evidence_test").first()

    rep1 = Report(
        id="r1",
        incident_type="accident",
        claimed_event_time=t0 - timedelta(minutes=5),
        submitted_at=t0 - timedelta(minutes=5),
        available_at=t0 - timedelta(minutes=5),
        segment_id="seg_evidence_test",
        location_description="Mile 1",
        latitude=40.75,
        longitude=-73.98,
        reporter_reference="user_1",
        description="Accident",
    )
    test_db.add(rep1)
    test_db.commit()

    ev_orig = Evidence(
        id="ev1",
        report_id="r1",
        content_hash="hash_unique_123",
        storage_path="/path1",
        media_type="image/jpeg",
        file_size_bytes=1000,
        is_duplicate=False,
        submitted_at=t0,
        available_at=t0,
    )
    test_db.add(ev_orig)
    test_db.commit()

    # Base assessment with 1 unique evidence
    result_with_one = assess_evidence_for_reports(test_db, [rep1], seg, replay_time=t0)
    score_one = result_with_one.heuristic_support_score

    # Add duplicate evidence to a second report
    rep2 = Report(
        id="r2",
        incident_type="accident",
        claimed_event_time=t0 - timedelta(minutes=3),
        submitted_at=t0 - timedelta(minutes=3),
        available_at=t0 - timedelta(minutes=3),
        segment_id="seg_evidence_test",
        location_description="Mile 1",
        latitude=40.75,
        longitude=-73.98,
        reporter_reference="user_2",
        description="Accident repeat",
    )
    test_db.add(rep2)
    test_db.commit()

    ev_dup = Evidence(
        id="ev2",
        report_id="r2",
        content_hash="hash_unique_123",  # Same hash
        storage_path="/path1",
        media_type="image/jpeg",
        file_size_bytes=1000,
        is_duplicate=True,  # Server flagged duplicate
        duplicate_of_id="ev1",
        submitted_at=t0,
        available_at=t0,
    )
    test_db.add(ev_dup)
    test_db.commit()

    result_with_dup = assess_evidence_for_reports(test_db, [rep1, rep2], seg, replay_time=t0)
    assert len(result_with_dup.duplicate_exclusions) >= 1
    assert "awarded 0 independent weight" in result_with_dup.duplicate_exclusions[0]


def test_shared_source_dependency_grouping(test_db):
    t0 = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)
    seg = test_db.query(RoadSegment).filter_by(id="seg_evidence_test").first()

    # Three reports from the SAME dependency group
    reps = [
        Report(
            id=f"rep_dep_{i}",
            incident_type="debris",
            claimed_event_time=t0 - timedelta(minutes=5),
            submitted_at=t0 - timedelta(minutes=5),
            available_at=t0 - timedelta(minutes=5),
            segment_id="seg_evidence_test",
            location_description="Location",
            latitude=40.75,
            longitude=-73.98,
            reporter_reference=f"patrol_{i}",
            dependency_group_id="dep_same_patrol_fleet",
            description="Debris",
        )
        for i in range(3)
    ]
    test_db.add_all(reps)
    test_db.commit()

    result = assess_evidence_for_reports(test_db, reps, seg, replay_time=t0)
    assert len(result.dependencies) >= 1
    assert "capped at single source" in result.dependencies[0]


def test_future_claimed_timestamp_flagged(test_db):
    t0 = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)
    seg = test_db.query(RoadSegment).filter_by(id="seg_evidence_test").first()

    # Report with claimed event time 40 minutes into the future
    future_rep = Report(
        id="rep_future",
        incident_type="accident",
        claimed_event_time=t0 + timedelta(minutes=40),  # Future!
        submitted_at=t0,
        available_at=t0,
        segment_id="seg_evidence_test",
        location_description="Junction",
        latitude=40.75,
        longitude=-73.98,
        reporter_reference="usr_x",
        description="Future prediction claim",
    )
    test_db.add(future_rep)
    test_db.commit()

    result = assess_evidence_for_reports(test_db, [future_rep], seg, replay_time=t0)
    assert len(result.contradictions) >= 1
    assert "in the future" in result.contradictions[0]


def test_sensor_speed_contradiction_detection(test_db):
    t0 = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)
    seg = test_db.query(RoadSegment).filter_by(id="seg_evidence_test").first()

    # Sensor reports free-flow (15.0 m/s = 100% of free-flow 15.0 m/s) at 08:28
    obs = Observation(
        id="obs_free_flow",
        segment_id="seg_evidence_test",
        observed_at=t0 - timedelta(minutes=2),
        available_at=t0 - timedelta(minutes=2),
        value=15.0,
        unit="mps",
    )
    test_db.add(obs)

    # Report claims severe accident blockage at 08:27
    rep = Report(
        id="rep_blocked",
        incident_type="accident",
        claimed_event_time=t0 - timedelta(minutes=3),
        submitted_at=t0 - timedelta(minutes=3),
        available_at=t0 - timedelta(minutes=3),
        segment_id="seg_evidence_test",
        location_description="Mile 2",
        latitude=40.75,
        longitude=-73.98,
        reporter_reference="usr_y",
        description="Total road blockage",
    )
    test_db.add(rep)
    test_db.commit()

    result = assess_evidence_for_reports(test_db, [rep], seg, replay_time=t0)
    assert any("shows normal free-flow" in c for c in result.contradictions)
