"""Unit tests for UTC-aware timestamp handling and temporal replay filtering."""

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
from backend.app.models import Base, Observation, RoadSegment


@pytest.fixture
def temp_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Create base segment
        seg = RoadSegment(
            id="seg_temp_test",
            name="Temporal Test Road",
            source_node="n1",
            target_node="n2",
            directed_edge_id="edge_0",
            length_meters=1000.0,
            free_flow_speed_mps=14.0,
            geometry_json="[]",
        )
        session.add(seg)
        session.commit()
        yield session
    finally:
        session.close()


def test_utc_datetime_timezone_awareness(temp_db):
    naive_dt = datetime(2026, 10, 15, 8, 30, 0)
    aware_dt = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)

    obs = Observation(
        id="obs_tz_test",
        segment_id="seg_temp_test",
        observed_at=naive_dt,
        available_at=aware_dt,
        value=12.0,
    )
    temp_db.add(obs)
    temp_db.commit()

    retrieved = temp_db.query(Observation).filter_by(id="obs_tz_test").first()
    assert retrieved.observed_at.tzinfo is not None
    assert retrieved.observed_at.tzinfo == timezone.utc
    assert retrieved.available_at.tzinfo == timezone.utc


def test_replay_temporal_eligibility_filter(temp_db):
    """At replay time T, observations with available_at > T must remain INVISIBLE."""
    t0 = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)

    # 1. Normal observation (observed 08:20, available 08:21) -> ELIGIBLE at t0
    obs_normal = Observation(
        id="obs_normal",
        segment_id="seg_temp_test",
        observed_at=t0 - timedelta(minutes=10),
        available_at=t0 - timedelta(minutes=9),
        value=14.0,
    )

    # 2. Late-arriving observation (observed 08:15, available 08:45) -> INVISIBLE at t0
    obs_late = Observation(
        id="obs_late",
        segment_id="seg_temp_test",
        observed_at=t0 - timedelta(minutes=15),
        available_at=t0 + timedelta(minutes=15),  # Available at 08:45
        value=4.0,
    )

    temp_db.add_all([obs_normal, obs_late])
    temp_db.commit()

    # Query snapshot as of t0 (08:30:00Z)
    eligible_at_t0 = (
        temp_db.query(Observation)
        .filter(
            Observation.segment_id == "seg_temp_test",
            Observation.available_at <= t0,
        )
        .all()
    )
    eligible_ids_t0 = {o.id for o in eligible_at_t0}
    assert "obs_normal" in eligible_ids_t0
    assert "obs_late" not in eligible_ids_t0, "Late observation leaked before its available_at time!"

    # Query snapshot after advancing replay to t0 + 20m (08:50:00Z)
    t_advanced = t0 + timedelta(minutes=20)
    eligible_at_advanced = (
        temp_db.query(Observation)
        .filter(
            Observation.segment_id == "seg_temp_test",
            Observation.available_at <= t_advanced,
        )
        .all()
    )
    eligible_ids_adv = {o.id for o in eligible_at_advanced}
    assert "obs_normal" in eligible_ids_adv
    assert "obs_late" in eligible_ids_adv, "Late observation should become visible once available_at is passed!"


def test_observed_at_vs_available_at_preserved(temp_db):
    t_obs = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)
    t_avail = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)

    obs = Observation(
        id="obs_preservation",
        segment_id="seg_temp_test",
        observed_at=t_obs,
        available_at=t_avail,
        value=11.5,
    )
    temp_db.add(obs)
    temp_db.commit()

    retrieved = temp_db.query(Observation).filter_by(id="obs_preservation").first()
    assert retrieved.observed_at == t_obs
    assert retrieved.available_at == t_avail
    assert retrieved.available_at > retrieved.observed_at
