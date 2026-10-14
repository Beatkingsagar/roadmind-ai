"""Unit tests for SQLAlchemy model relationships, foreign keys, and constraints."""

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
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from backend.app.models import (
    Base,
    Evidence,
    IncidentEpisode,
    Observation,
    Report,
    RoadSegment,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_road_segment_creation_and_properties(db_session):
    seg = RoadSegment(
        id="seg_test_100",
        name="Test Expressway",
        source_node="n1",
        target_node="n2",
        directed_edge_id="edge_0",
        length_meters=2000.0,
        free_flow_speed_mps=20.0,  # 72 km/h
        geometry_json="[[-73.98, 40.75], [-73.97, 40.75]]",
    )
    db_session.add(seg)
    db_session.commit()

    retrieved = db_session.query(RoadSegment).filter_by(id="seg_test_100").first()
    assert retrieved is not None
    assert retrieved.free_flow_speed_kmph == 72.0
    assert retrieved.free_flow_travel_time_seconds == 100.0
    assert len(retrieved.coordinates) == 2


def test_parallel_edges_unique_constraint(db_session):
    # Two edges with different directed_edge_id between same nodes should SUCCEED
    edge_a = RoadSegment(
        id="seg_edge_a",
        name="Local",
        source_node="node_X",
        target_node="node_Y",
        directed_edge_id="edge_local",
        length_meters=1000.0,
        free_flow_speed_mps=10.0,
        geometry_json="[]",
    )
    edge_b = RoadSegment(
        id="seg_edge_b",
        name="Express",
        source_node="node_X",
        target_node="node_Y",
        directed_edge_id="edge_express",
        length_meters=1000.0,
        free_flow_speed_mps=20.0,
        geometry_json="[]",
    )
    db_session.add_all([edge_a, edge_b])
    db_session.commit()

    # Third edge with DUPLICATE (source_node, target_node, directed_edge_id) should FAIL
    edge_duplicate = RoadSegment(
        id="seg_edge_c",
        name="Duplicate Edge",
        source_node="node_X",
        target_node="node_Y",
        directed_edge_id="edge_local",  # Duplicate of edge_a!
        length_meters=1000.0,
        free_flow_speed_mps=10.0,
        geometry_json="[]",
    )
    db_session.add(edge_duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_enforcement(db_session):
    now = datetime.now(timezone.utc)
    # Inserting observation referencing nonexistent segment should FAIL with PRAGMA foreign_keys=ON
    invalid_obs = Observation(
        id="obs_orphan",
        segment_id="nonexistent_segment",
        observed_at=now,
        available_at=now,
        value=15.0,
    )
    db_session.add(invalid_obs)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_report_to_evidence(db_session):
    now = datetime.now(timezone.utc)
    seg = RoadSegment(
        id="seg_base_01",
        name="Base Road",
        source_node="A",
        target_node="B",
        directed_edge_id="edge_0",
        length_meters=1000.0,
        free_flow_speed_mps=15.0,
        geometry_json="[]",
    )
    db_session.add(seg)
    db_session.commit()

    rep = Report(
        id="rep_test_01",
        incident_type="accident",
        claimed_event_time=now,
        submitted_at=now,
        available_at=now,
        segment_id="seg_base_01",
        location_description="Point A",
        latitude=40.75,
        longitude=-73.98,
        reporter_reference="user1",
        description="Collision",
    )
    db_session.add(rep)
    db_session.commit()

    ev = Evidence(
        id="ev_test_01",
        report_id="rep_test_01",
        content_hash="abc123hash",
        storage_path="/private/ev/abc123hash.jpg",
        media_type="image/jpeg",
        file_size_bytes=1024,
    )
    db_session.add(ev)
    db_session.commit()

    # Evidence exists
    assert db_session.query(Evidence).filter_by(id="ev_test_01").first() is not None

    # Delete Report -> Cascade delete should remove Evidence
    db_session.delete(rep)
    db_session.commit()

    assert db_session.query(Evidence).filter_by(id="ev_test_01").first() is None
