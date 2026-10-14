"""Unit tests for Road Memory and Inspection Priority Engine."""

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
from backend.app.models import Observation, Report, RoadSegment
from backend.app.services.memory import (
    build_segment_memory_summaries,
    cluster_reports_into_episodes,
    compute_observation_coverage,
    rank_inspection_priorities,
)


def _make_report(
    rep_id: str,
    segment_id: str,
    event_time: datetime,
    available_at: datetime,
    lat: float = 40.75,
    lon: float = -73.98,
    incident_type: str = "pothole",
    reporter: str = "user_1",
    dep_group: str | None = None,
) -> Report:
    return Report(
        id=rep_id,
        segment_id=segment_id,
        claimed_event_time=event_time,
        submitted_at=event_time,
        available_at=available_at,
        latitude=lat,
        longitude=lon,
        incident_type=incident_type,
        location_description=f"Near {segment_id}",
        reporter_reference=reporter,
        dependency_group_id=dep_group,
        description="Hazard report",
        data_mode="user_submitted",
    )


def test_duplicate_reports_grouped_into_single_episode():
    """Verify that multiple reports for the same incident are clustered into 1 episode."""
    t0 = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=15)
    t2 = t0 + timedelta(minutes=45)

    reports = [
        _make_report("r1", "seg_corridor", t0, t0, reporter="user_a"),
        _make_report("r2", "seg_corridor", t1, t1, reporter="user_b"),
        _make_report("r3", "seg_corridor", t2, t2, reporter="user_c"),
    ]

    episodes = cluster_reports_into_episodes(reports, temporal_threshold_hours=4.0)
    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.segment_id == "seg_corridor"
    assert ep.report_count == 3
    assert ep.unique_source_count == 3
    assert ep.duration_minutes == 45.0
    assert ep.first_reported_at == t0
    assert ep.last_reported_at == t2


def test_distinct_episodes_separated_in_time():
    """Verify distinct episodes separated by weeks are not lumped together."""
    t_sep = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    t_oct = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)

    reports = [
        _make_report("r_sep1", "seg_corridor", t_sep, t_sep),
        _make_report("r_oct1", "seg_corridor", t_oct, t_oct),
    ]

    episodes = cluster_reports_into_episodes(reports, temporal_threshold_hours=4.0)
    assert len(episodes) == 2
    assert {ep.first_reported_at for ep in episodes} == {t_sep, t_oct}


def test_spatial_radius_clustering():
    """Verify reports on nearby coordinates within threshold cluster together."""
    t0 = datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=10)

    # Coordinates ~111 meters apart (0.001 degree lat is ~111m)
    rep1 = _make_report("r1", "seg_a", t0, t0, lat=40.7500, lon=-73.9800)
    rep2 = _make_report("r2", "seg_a", t1, t1, lat=40.7510, lon=-73.9800)

    episodes = cluster_reports_into_episodes(
        [rep1, rep2], spatial_threshold_meters=200.0, temporal_threshold_hours=2.0
    )
    assert len(episodes) == 1
    assert episodes[0].report_count == 2


def test_observation_coverage_reporting_poor_vs_sufficient():
    """Verify poor coverage flags absence of reports as unverified, not safe."""
    t0 = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)

    # 1. Zero observations
    cov_zero = compute_observation_coverage([], segment_id="seg_unmonitored")
    assert cov_zero.observation_count == 0
    assert cov_zero.is_coverage_poor is True
    assert "cannot be interpreted as road safety" in cov_zero.coverage_limitation_note

    # 2. Sparse observations (2 observations < threshold of 5)
    obs_sparse = [
        Observation(id="o1", segment_id="seg_sparse", observed_at=t0, available_at=t0, value=12.0, unit="mps", quality_score=1.0, provenance="s", data_mode="s"),
        Observation(id="o2", segment_id="seg_sparse", observed_at=t0 + timedelta(hours=1), available_at=t0 + timedelta(hours=1), value=11.5, unit="mps", quality_score=1.0, provenance="s", data_mode="s"),
    ]
    cov_sparse = compute_observation_coverage(obs_sparse, segment_id="seg_sparse")
    assert cov_sparse.is_coverage_poor is True
    assert "Sparse observation coverage" in cov_sparse.coverage_limitation_note

    # 3. Sufficient observations (6 observations >= threshold of 5)
    obs_good = [
        Observation(id=f"o_{i}", segment_id="seg_good", observed_at=t0 + timedelta(minutes=i*10), available_at=t0 + timedelta(minutes=i*10), value=12.0, unit="mps", quality_score=1.0, provenance="s", data_mode="s")
        for i in range(6)
    ]
    cov_good = compute_observation_coverage(obs_good, segment_id="seg_good")
    assert cov_good.is_coverage_poor is False
    assert cov_good.coverage_limitation_note is None


def test_inspection_priority_scoring_and_explanation():
    """Verify transparent priority scoring matches calculated components."""
    t_sep = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    t_oct = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)

    seg_high = RoadSegment(id="seg_high", name="Problem Corridor", source_node="n1", target_node="n2", length_meters=1000.0, free_flow_speed_mps=15.0)
    seg_low = RoadSegment(id="seg_low", name="Quiet Lane", source_node="n3", target_node="n4", length_meters=500.0, free_flow_speed_mps=10.0)

    # High priority segment has 2 distinct episodes, one lasting 120 minutes
    reps_high = [
        _make_report("r1", "seg_high", t_sep, t_sep),
        _make_report("r2", "seg_high", t_oct, t_oct),
        _make_report("r3", "seg_high", t_oct + timedelta(minutes=120), t_oct + timedelta(minutes=120)),
    ]
    # Low priority segment has 0 reports
    reps_low = []

    # Sufficient observations for high, zero for low
    obs_high = [
        Observation(id=f"oh_{i}", segment_id="seg_high", observed_at=t_oct + timedelta(minutes=i*10), available_at=t_oct + timedelta(minutes=i*10), value=14.0, unit="mps", quality_score=1.0, provenance="s", data_mode="s")
        for i in range(6)
    ]

    summaries = build_segment_memory_summaries(
        segments=[seg_high, seg_low],
        reports=reps_high + reps_low,
        observations=obs_high,
    )

    ranked = rank_inspection_priorities(summaries)
    assert len(ranked) == 2
    top = ranked[0]
    assert top.segment_id == "seg_high"
    assert top.priority_rank == 1
    assert top.observed_recurrence_score == 30.0  # 2 episodes * 15.0 pts = 30.0
    assert top.severity_score == 12.0  # medium = 12.0
    # Explanation must be transparent and match points
    assert "Inspection Priority:" in top.explanation
    assert "Recurrence: 30.0pts" in top.explanation
    assert "Severity: 12.0pts" in top.explanation
    assert any("Vehicle exposure data unavailable" in lim for lim in top.data_limitations)


def test_temporal_replay_filtering_in_memory():
    """Verify that records available after replay_time are strictly excluded from memory."""
    replay_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

    # Report available before replay time
    rep_past = _make_report("r_past", "seg_corridor", replay_time - timedelta(hours=2), replay_time - timedelta(hours=1))
    # Report available after replay time
    rep_future = _make_report("r_future", "seg_corridor", replay_time - timedelta(minutes=30), replay_time + timedelta(minutes=10))

    episodes = cluster_reports_into_episodes([rep_past, rep_future], replay_time=replay_time)
    assert len(episodes) == 1
    assert episodes[0].report_ids == ["r_past"]
    assert "r_future" not in episodes[0].report_ids
