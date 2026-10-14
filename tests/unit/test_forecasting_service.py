"""Unit tests for the Forecasting Engine and Chronological Outcome Evaluation."""

from __future__ import annotations

import math
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
from backend.app.models.observation import Observation
from backend.app.schemas.common import AbstentionReason
from backend.app.services.forecasting import (
    evaluate_chronological_predictions,
    generate_historical_median_forecast,
    generate_persistence_forecast,
)


def _make_obs(
    obs_id: str,
    segment_id: str,
    observed_at: datetime,
    available_at: datetime,
    speed_mps: float,
    unit: str = "mps",
) -> Observation:
    return Observation(
        id=obs_id,
        segment_id=segment_id,
        observed_at=observed_at,
        available_at=available_at,
        value=speed_mps,
        unit=unit,
        quality_score=1.0,
        provenance="unit_test",
        data_mode="synthetic",
    )


def test_persistence_forecast_success():
    base_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    obs = [
        _make_obs("o1", "seg_1", base_time - timedelta(minutes=20), base_time - timedelta(minutes=19), 15.0),
        _make_obs("o2", "seg_1", base_time - timedelta(minutes=5), base_time - timedelta(minutes=4), 12.5),
    ]

    forecast = generate_persistence_forecast(obs, segment_id="seg_1", issue_time=base_time, horizon_minutes=15)
    assert forecast.is_abstained is False
    assert forecast.predicted_speed_mps == 12.5
    assert forecast.horizon_minutes == 15
    assert forecast.target_time == base_time + timedelta(minutes=15)
    assert forecast.interval_lower_mps == round(12.5 * 0.85, 2)
    assert forecast.interval_upper_mps == round(12.5 * 1.15, 2)


def test_persistence_forecast_abstain_stale():
    base_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    # Observation is 90 minutes old (> 60 minute freshness window)
    obs = [
        _make_obs("o1", "seg_1", base_time - timedelta(minutes=90), base_time - timedelta(minutes=80), 14.0),
    ]

    forecast = generate_persistence_forecast(
        obs, segment_id="seg_1", issue_time=base_time, max_freshness_minutes=60
    )
    assert forecast.is_abstained is True
    assert forecast.abstention_reason == AbstentionReason.STALE_OBSERVATIONS
    assert forecast.predicted_speed_mps is None


def test_persistence_forecast_abstain_unobserved():
    base_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    forecast = generate_persistence_forecast([], segment_id="seg_unobserved", issue_time=base_time)
    assert forecast.is_abstained is True
    assert forecast.abstention_reason == AbstentionReason.UNOBSERVED_SEGMENT


def test_historical_median_forecast_success():
    # Wednesday at 14:00 UTC
    target_wed = datetime(2026, 10, 14, 14, 15, tzinfo=timezone.utc)
    issue_wed = target_wed - timedelta(minutes=15)  # 14:00

    # Past 3 Wednesdays around 14:15 UTC (e.g. 14:10, 14:15, 14:20)
    wed_minus_1 = target_wed - timedelta(days=7)
    wed_minus_2 = target_wed - timedelta(days=14)
    wed_minus_3 = target_wed - timedelta(days=21)

    obs = [
        _make_obs("o1", "seg_1", wed_minus_1, wed_minus_1 + timedelta(minutes=1), 10.0),
        _make_obs("o2", "seg_1", wed_minus_2, wed_minus_2 + timedelta(minutes=1), 14.0),
        _make_obs("o3", "seg_1", wed_minus_3, wed_minus_3 + timedelta(minutes=1), 12.0),
    ]

    forecast = generate_historical_median_forecast(
        obs, segment_id="seg_1", issue_time=issue_wed, horizon_minutes=15, min_history_samples=3
    )
    assert forecast.is_abstained is False
    assert forecast.predicted_speed_mps == 12.0  # Median of 10.0, 12.0, 14.0 is 12.0
    assert forecast.interval_lower_mps == 10.0
    assert forecast.interval_upper_mps == 14.0


def test_historical_median_abstain_insufficient_history():
    target_wed = datetime(2026, 10, 14, 14, 15, tzinfo=timezone.utc)
    issue_wed = target_wed - timedelta(minutes=15)

    # Only 2 past observations available (minimum required is 3)
    wed_minus_1 = target_wed - timedelta(days=7)
    wed_minus_2 = target_wed - timedelta(days=14)

    obs = [
        _make_obs("o1", "seg_1", wed_minus_1, wed_minus_1 + timedelta(minutes=1), 10.0),
        _make_obs("o2", "seg_1", wed_minus_2, wed_minus_2 + timedelta(minutes=1), 14.0),
    ]

    forecast = generate_historical_median_forecast(
        obs, segment_id="seg_1", issue_time=issue_wed, horizon_minutes=15, min_history_samples=3
    )
    assert forecast.is_abstained is True
    assert forecast.abstention_reason == AbstentionReason.INSUFFICIENT_HISTORY


def test_future_observation_leakage_prevented():
    """Verify that an observation whose available_at > issue_time is strictly excluded."""
    issue_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

    # Observation was observed at 11:55, but only available at 12:05 (5 minutes after issue time)
    late_obs = _make_obs(
        "o_late", "seg_1",
        observed_at=issue_time - timedelta(minutes=5),
        available_at=issue_time + timedelta(minutes=5),
        speed_mps=5.0,  # Sudden congestion
    )
    # Earlier available observation at 11:30
    early_obs = _make_obs(
        "o_early", "seg_1",
        observed_at=issue_time - timedelta(minutes=30),
        available_at=issue_time - timedelta(minutes=25),
        speed_mps=15.0,
    )

    forecast = generate_persistence_forecast(
        [late_obs, early_obs], segment_id="seg_1", issue_time=issue_time, horizon_minutes=15
    )
    # Must use early_obs (15.0 mps), NOT the late-arriving observation (5.0 mps)
    assert forecast.is_abstained is False
    assert forecast.predicted_speed_mps == 15.0


def test_chronological_evaluation_mae_rmse_calculation():
    """Verify hand-calculable MAE and RMSE calculation across multiple horizons."""
    issue_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    target_15m = issue_time + timedelta(minutes=15)
    target_30m = issue_time + timedelta(minutes=30)
    eval_time = issue_time + timedelta(minutes=60)

    # 15m Horizon Predictions:
    # Pred A: 10.0 mps, actual: 12.0 mps -> error: -2.0, abs: 2.0, sq: 4.0
    # Pred B: 15.0 mps, actual: 13.0 mps -> error: +2.0, abs: 2.0, sq: 4.0
    # Expected 15m: MAE = (2+2)/2 = 2.0, RMSE = sqrt((4+4)/2) = 2.0
    pred_15a = generate_persistence_forecast(
        [_make_obs("o1", "seg_a", issue_time - timedelta(minutes=5), issue_time, 10.0)],
        segment_id="seg_a", issue_time=issue_time, horizon_minutes=15
    )
    pred_15b = generate_persistence_forecast(
        [_make_obs("o2", "seg_b", issue_time - timedelta(minutes=5), issue_time, 15.0)],
        segment_id="seg_b", issue_time=issue_time, horizon_minutes=15
    )

    # 30m Horizon Prediction:
    # Pred C: 20.0 mps, actual: 16.0 mps -> error: 4.0, abs: 4.0, sq: 16.0
    # Expected 30m: MAE = 4.0, RMSE = 4.0
    pred_30c = generate_persistence_forecast(
        [_make_obs("o3", "seg_c", issue_time - timedelta(minutes=5), issue_time, 20.0)],
        segment_id="seg_c", issue_time=issue_time, horizon_minutes=30
    )

    # Actual observations revealed in the future
    actuals = [
        _make_obs("act_1", "seg_a", target_15m, target_15m + timedelta(minutes=1), 12.0),
        _make_obs("act_2", "seg_b", target_15m, target_15m + timedelta(minutes=1), 13.0),
        _make_obs("act_3", "seg_c", target_30m, target_30m + timedelta(minutes=1), 16.0),
    ]

    evals, summaries, metadata = evaluate_chronological_predictions(
        [pred_15a, pred_15b, pred_30c],
        actuals,
        evaluation_time=eval_time,
    )

    assert len(evals) == 3
    assert metadata["evaluated_count"] == 3
    assert metadata["abstained_count"] == 0

    # Check 15m summary
    summary_15 = summaries[15]
    assert summary_15.sample_count == 2
    assert summary_15.mae_mps == 2.0
    assert summary_15.rmse_mps == 2.0

    # Check 30m summary
    summary_30 = summaries[30]
    assert summary_30.sample_count == 1
    assert summary_30.mae_mps == 4.0
    assert summary_30.rmse_mps == 4.0


def test_chronological_evaluation_excludes_unrevealed_actuals():
    """Verify that actual observations not yet available at evaluation_time are excluded."""
    issue_time = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    target_15m = issue_time + timedelta(minutes=15)
    # Evaluation run at target time exactly (12:15)
    eval_time = target_15m

    pred = generate_persistence_forecast(
        [_make_obs("o1", "seg_a", issue_time - timedelta(minutes=5), issue_time, 10.0)],
        segment_id="seg_a", issue_time=issue_time, horizon_minutes=15
    )

    # Actual observation observed at 12:15, but network delay makes it available at 12:20 (> eval_time)
    future_available_act = _make_obs(
        "act_late", "seg_a",
        observed_at=target_15m,
        available_at=eval_time + timedelta(minutes=5),
        speed_mps=12.0,
    )

    evals, summaries, metadata = evaluate_chronological_predictions(
        [pred],
        [future_available_act],
        evaluation_time=eval_time,
    )

    # Should NOT match because actual was not available at eval_time
    assert len(evals) == 0
    assert metadata["evaluated_count"] == 0
    assert metadata["missing_actual_count"] == 1
