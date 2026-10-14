"""Unit tests for Pydantic schema validation, unit conversions, and boundaries."""

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
from pydantic import ValidationError
from backend.app.schemas import (
    AbstentionReason,
    DataMode,
    IncidentType,
    ObservationBase,
    ReportCreate,
    RoadSegmentBase,
    ScenarioOverride,
)


def test_road_segment_schema_valid():
    seg = RoadSegmentBase(
        id="seg_test_01",
        name="Test Corridor",
        source_node="node_A",
        target_node="node_B",
        directed_edge_id="edge_0",
        length_meters=1500.0,
        free_flow_speed_mps=15.0,
        data_mode=DataMode.SYNTHETIC,
    )
    assert seg.length_meters == 1500.0
    assert seg.free_flow_speed_mps == 15.0
    assert seg.data_mode == DataMode.SYNTHETIC


def test_road_segment_negative_length_rejected():
    with pytest.raises(ValidationError):
        RoadSegmentBase(
            id="seg_invalid",
            name="Invalid Corridor",
            source_node="node_A",
            target_node="node_B",
            directed_edge_id="edge_0",
            length_meters=-10.0,  # Invalid
            free_flow_speed_mps=15.0,
        )


def test_road_segment_zero_speed_rejected():
    with pytest.raises(ValidationError):
        RoadSegmentBase(
            id="seg_invalid_speed",
            name="Invalid Speed",
            source_node="node_A",
            target_node="node_B",
            directed_edge_id="edge_0",
            length_meters=500.0,
            free_flow_speed_mps=0.0,  # Invalid: traversable road must have positive speed
        )


def test_observation_schema_validation():
    now = datetime.now(timezone.utc)
    obs = ObservationBase(
        segment_id="seg_test_01",
        observed_at=now,
        available_at=now,
        value=14.5,
        unit="mps",
        quality_score=0.95,
    )
    assert obs.value == 14.5
    assert obs.quality_score == 0.95

    # Negative quality score rejected
    with pytest.raises(ValidationError):
        ObservationBase(
            segment_id="seg_test_01",
            observed_at=now,
            available_at=now,
            value=14.5,
            quality_score=-0.1,
        )


def test_report_create_validation():
    now = datetime.now(timezone.utc)
    rep = ReportCreate(
        incident_type=IncidentType.ACCIDENT,
        claimed_event_time=now,
        segment_id="seg_test_01",
        location_description="Mile Marker 12",
        latitude=40.7500,
        longitude=-73.9800,
        description="Fender bender blocking traffic",
    )
    assert rep.incident_type == IncidentType.ACCIDENT

    # Latitude out of bounds rejected
    with pytest.raises(ValidationError):
        ReportCreate(
            incident_type=IncidentType.ACCIDENT,
            claimed_event_time=now,
            segment_id="seg_test_01",
            location_description="Invalid Latitude",
            latitude=95.0,  # Out of range [-90, 90]
            longitude=-73.9800,
            description="Test invalid coordinate",
        )


def test_scenario_override_validation():
    override = ScenarioOverride(closed=False, speed_mps=5.0, delay_seconds=60.0)
    assert override.delay_seconds == 60.0
    assert override.speed_mps == 5.0

    # Negative delay rejected
    with pytest.raises(ValidationError):
        ScenarioOverride(closed=False, delay_seconds=-10.0)
