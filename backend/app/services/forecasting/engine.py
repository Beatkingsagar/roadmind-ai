"""Forecasting Engine for RoadMind AI.

Implements deterministic baseline speed forecasting and chronological outcome evaluation:
1. Persistence Forecast:
   - Predicts the latest valid observed speed for the segment prior to issue_time.
   - Enforces freshness checks (abstains on STALE_OBSERVATIONS).
2. Historical Time-of-Week Median:
   - Slices observations matching the same day of week and time-of-day window.
   - Requires minimum historical sample count (abstains on INSUFFICIENT_HISTORY).
3. Chronological Outcome Evaluation:
   - Evaluates predictions only against observations that were physically observed
     and made available at or before evaluation_time.
   - Calculates MAE, RMSE, and interval coverage separately per horizon (15m, 30m).
   - Never rewrites historical predictions.
   - Explicitly records sample counts, missingness, and exclusions.
"""

from __future__ import annotations

import hashlib
import math
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.models.observation import Observation
from backend.app.models.prediction import Prediction
from backend.app.schemas.common import AbstentionReason, DataMode
from backend.app.schemas.evaluation import EvaluationSummary, OutcomeEvaluationResponse
from backend.app.schemas.prediction import PredictionResponse

MODEL_VERSION_PERSISTENCE = "persistence_baseline_v1"
MODEL_VERSION_HISTORICAL_MEDIAN = "historical_median_v1"
EVALUATION_VERSION = "eval_v1.0"


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_snapshot_hash(observations: List[Observation]) -> str:
    """Deterministic hash of observation IDs in the input snapshot."""
    sorted_ids = sorted([str(o.id) for o in observations])
    raw = "|".join(sorted_ids)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"snap_{digest}"


def generate_persistence_forecast(
    observations: List[Observation],
    segment_id: str,
    issue_time: datetime,
    horizon_minutes: int = 15,
    max_freshness_minutes: int = 60,
    confidence_level: float = 0.90,
) -> PredictionResponse:
    """Generate a persistence forecast for a road segment.
    
    Predicts the most recent observed speed available at or before issue_time.
    Abstains if no observations exist or if the latest observation is older than max_freshness_minutes.
    """
    issue_utc = _ensure_utc(issue_time)
    target_utc = issue_utc + timedelta(minutes=horizon_minutes)

    # 1. Temporal filter: Only observations available at or before issue_time
    eligible_obs = [
        o for o in observations
        if o.segment_id == segment_id and _ensure_utc(o.available_at) <= issue_utc
    ]

    snapshot_ref = _compute_snapshot_hash(eligible_obs)
    pred_id = f"pred_pers_{uuid.uuid4().hex[:8]}"

    # Check for unit validity
    for o in eligible_obs:
        if o.unit not in ("mps", "kmph"):
            return PredictionResponse(
                id=pred_id,
                segment_id=segment_id,
                issue_time=issue_utc,
                target_time=target_utc,
                horizon_minutes=horizon_minutes,
                model_version=MODEL_VERSION_PERSISTENCE,
                input_snapshot_reference=snapshot_ref,
                confidence_level=confidence_level,
                abstention_reason=AbstentionReason.INVALID_UNITS,
                is_abstained=True,
                data_mode=DataMode.SYNTHETIC,
            )

    if not eligible_obs:
        return PredictionResponse(
            id=pred_id,
            segment_id=segment_id,
            issue_time=issue_utc,
            target_time=target_utc,
            horizon_minutes=horizon_minutes,
            model_version=MODEL_VERSION_PERSISTENCE,
            input_snapshot_reference=snapshot_ref,
            confidence_level=confidence_level,
            abstention_reason=AbstentionReason.UNOBSERVED_SEGMENT,
            is_abstained=True,
            data_mode=DataMode.SYNTHETIC,
        )

    # Sort descending by observed_at to find the freshest observation
    eligible_obs.sort(key=lambda o: _ensure_utc(o.observed_at), reverse=True)
    latest_obs = eligible_obs[0]
    obs_time_utc = _ensure_utc(latest_obs.observed_at)

    # Freshness check
    age_seconds = (issue_utc - obs_time_utc).total_seconds()
    if age_seconds < 0:
        # Observation observed in the future relative to issue_time (inconsistency)
        age_seconds = 0.0

    if age_seconds > (max_freshness_minutes * 60):
        return PredictionResponse(
            id=pred_id,
            segment_id=segment_id,
            issue_time=issue_utc,
            target_time=target_utc,
            horizon_minutes=horizon_minutes,
            model_version=MODEL_VERSION_PERSISTENCE,
            input_snapshot_reference=snapshot_ref,
            confidence_level=confidence_level,
            abstention_reason=AbstentionReason.STALE_OBSERVATIONS,
            is_abstained=True,
            data_mode=DataMode.SYNTHETIC,
        )

    # Valid forecast
    pred_speed = round(latest_obs.speed_mps, 2)
    # Documented baseline interval: ±15% around persistence speed
    lower_bound = max(0.0, round(pred_speed * 0.85, 2))
    upper_bound = round(pred_speed * 1.15, 2)

    return PredictionResponse(
        id=pred_id,
        segment_id=segment_id,
        issue_time=issue_utc,
        target_time=target_utc,
        horizon_minutes=horizon_minutes,
        model_version=MODEL_VERSION_PERSISTENCE,
        input_snapshot_reference=snapshot_ref,
        predicted_speed_mps=pred_speed,
        predicted_speed_kmph=round(pred_speed * 3.6, 2),
        interval_lower_mps=lower_bound,
        interval_upper_mps=upper_bound,
        confidence_level=confidence_level,
        abstention_reason=None,
        is_abstained=False,
        data_mode=DataMode.SYNTHETIC,
    )


def generate_historical_median_forecast(
    observations: List[Observation],
    segment_id: str,
    issue_time: datetime,
    horizon_minutes: int = 15,
    min_history_samples: int = 3,
    time_of_day_window_minutes: int = 30,
    confidence_level: float = 0.90,
) -> PredictionResponse:
    """Generate a historical time-of-week median forecast for a road segment.
    
    Filters observations available at or before issue_time matching:
    - Same day of week (Monday=0 ... Sunday=6)
    - Time of day within ± time_of_day_window_minutes of target_time
    
    Requires at least min_history_samples; abstains if insufficient history exists.
    """
    issue_utc = _ensure_utc(issue_time)
    target_utc = issue_utc + timedelta(minutes=horizon_minutes)

    # 1. Temporal filter: observations available at or before issue_time
    eligible_obs = [
        o for o in observations
        if o.segment_id == segment_id and _ensure_utc(o.available_at) <= issue_utc
    ]

    snapshot_ref = _compute_snapshot_hash(eligible_obs)
    pred_id = f"pred_med_{uuid.uuid4().hex[:8]}"

    # Validate units
    for o in eligible_obs:
        if o.unit not in ("mps", "kmph"):
            return PredictionResponse(
                id=pred_id,
                segment_id=segment_id,
                issue_time=issue_utc,
                target_time=target_utc,
                horizon_minutes=horizon_minutes,
                model_version=MODEL_VERSION_HISTORICAL_MEDIAN,
                input_snapshot_reference=snapshot_ref,
                confidence_level=confidence_level,
                abstention_reason=AbstentionReason.INVALID_UNITS,
                is_abstained=True,
                data_mode=DataMode.SYNTHETIC,
            )

    target_weekday = target_utc.weekday()
    target_tod_minutes = target_utc.hour * 60 + target_utc.minute

    # 2. Filter by time-of-week compatibility
    compatible_speeds: List[float] = []
    for obs in eligible_obs:
        obs_utc = _ensure_utc(obs.observed_at)
        if obs_utc.weekday() != target_weekday:
            continue

        obs_tod_minutes = obs_utc.hour * 60 + obs_utc.minute
        diff_minutes = abs(obs_tod_minutes - target_tod_minutes)
        # Handle wrap around midnight if needed (1440 minutes in a day)
        diff_minutes = min(diff_minutes, 1440 - diff_minutes)

        if diff_minutes <= time_of_day_window_minutes:
            compatible_speeds.append(obs.speed_mps)

    # 3. Check sufficiency
    if len(compatible_speeds) < min_history_samples:
        return PredictionResponse(
            id=pred_id,
            segment_id=segment_id,
            issue_time=issue_utc,
            target_time=target_utc,
            horizon_minutes=horizon_minutes,
            model_version=MODEL_VERSION_HISTORICAL_MEDIAN,
            input_snapshot_reference=snapshot_ref,
            confidence_level=confidence_level,
            abstention_reason=AbstentionReason.INSUFFICIENT_HISTORY,
            is_abstained=True,
            data_mode=DataMode.SYNTHETIC,
        )

    # 4. Compute Median and Prediction Interval
    compatible_speeds.sort()
    med_speed = round(statistics.median(compatible_speeds), 2)

    # Nonparametric quantile interval: 10th and 90th percentile (or min/max if small sample)
    if len(compatible_speeds) >= 10:
        idx_lower = int(len(compatible_speeds) * 0.10)
        idx_upper = int(len(compatible_speeds) * 0.90)
        lower_bound = max(0.0, round(compatible_speeds[idx_lower], 2))
        upper_bound = round(compatible_speeds[min(idx_upper, len(compatible_speeds) - 1)], 2)
    else:
        # For small sample sizes (3-9), use min and max of compatible history
        lower_bound = max(0.0, round(compatible_speeds[0], 2))
        upper_bound = round(compatible_speeds[-1], 2)

    return PredictionResponse(
        id=pred_id,
        segment_id=segment_id,
        issue_time=issue_utc,
        target_time=target_utc,
        horizon_minutes=horizon_minutes,
        model_version=MODEL_VERSION_HISTORICAL_MEDIAN,
        input_snapshot_reference=snapshot_ref,
        predicted_speed_mps=med_speed,
        predicted_speed_kmph=round(med_speed * 3.6, 2),
        interval_lower_mps=lower_bound,
        interval_upper_mps=upper_bound,
        confidence_level=confidence_level,
        abstention_reason=None,
        is_abstained=False,
        data_mode=DataMode.SYNTHETIC,
    )


def evaluate_chronological_predictions(
    predictions: List[Union[Prediction, PredictionResponse]],
    observations: List[Observation],
    evaluation_time: datetime,
    tolerance_minutes: int = 5,
    dataset_scope: str = "synthetic_benchmark",
) -> Tuple[List[OutcomeEvaluationResponse], Dict[int, EvaluationSummary], Dict[str, Any]]:
    """Chronological evaluation of predictions against actual observations.
    
    Rules:
    - Only observations with available_at <= evaluation_time are eligible actuals.
    - Abstaining predictions are tracked in exclusions and excluded from MAE/RMSE calculations.
    - An actual observation is matched to a prediction if observed within ±tolerance_minutes of target_time.
    - Evaluates MAE and RMSE separately for each horizon (e.g. 15, 30 minutes).
    - Returns:
      1. List of individual OutcomeEvaluationResponse objects
      2. Dict mapping horizon_minutes -> EvaluationSummary
      3. Dict with tracking counts (total_predictions, evaluated_count, abstained_count, missing_actual_count)
    """
    eval_utc = _ensure_utc(evaluation_time)

    # Filter observations available at or before evaluation_time
    eligible_actuals = [
        o for o in observations
        if _ensure_utc(o.available_at) <= eval_utc
    ]

    evaluations: List[OutcomeEvaluationResponse] = []
    horizon_errors: Dict[int, List[float]] = {}
    horizon_within_intervals: Dict[int, List[bool]] = {}

    abstained_count = 0
    missing_actual_count = 0
    evaluated_count = 0

    for pred in predictions:
        h = pred.horizon_minutes
        if h not in horizon_errors:
            horizon_errors[h] = []
            horizon_within_intervals[h] = []

        # If prediction abstained, record exclusion
        if pred.is_abstained or pred.predicted_speed_mps is None:
            abstained_count += 1
            continue

        target_utc = _ensure_utc(pred.target_time)

        # Find closest compatible observation on the same segment
        candidate_actuals = [
            o for o in eligible_actuals
            if o.segment_id == pred.segment_id
            and abs((_ensure_utc(o.observed_at) - target_utc).total_seconds()) <= (tolerance_minutes * 60)
        ]

        if not candidate_actuals:
            missing_actual_count += 1
            continue

        # Choose the closest actual observation in time
        candidate_actuals.sort(
            key=lambda o: abs((_ensure_utc(o.observed_at) - target_utc).total_seconds())
        )
        matched_obs = candidate_actuals[0]

        actual_speed = matched_obs.speed_mps
        pred_speed = pred.predicted_speed_mps

        error = round(pred_speed - actual_speed, 3)
        abs_error = round(abs(error), 3)

        within = False
        if pred.interval_lower_mps is not None and pred.interval_upper_mps is not None:
            within = pred.interval_lower_mps <= actual_speed <= pred.interval_upper_mps

        eval_id = f"eval_{uuid.uuid4().hex[:8]}"
        eval_resp = OutcomeEvaluationResponse(
            id=eval_id,
            prediction_id=pred.id,
            observation_id=matched_obs.id,
            error_speed_mps=error,
            absolute_error_mps=abs_error,
            within_interval=within,
            evaluated_at=eval_utc,
            evaluation_version=EVALUATION_VERSION,
        )
        evaluations.append(eval_resp)

        horizon_errors[h].append(error)
        horizon_within_intervals[h].append(within)
        evaluated_count += 1

    # Compute MAE and RMSE separately for each horizon
    summaries: Dict[int, EvaluationSummary] = {}
    for h, errors in horizon_errors.items():
        count = len(errors)
        if count == 0:
            summaries[h] = EvaluationSummary(
                horizon_minutes=h,
                sample_count=0,
                mae_mps=0.0,
                rmse_mps=0.0,
                interval_coverage_pct=0.0,
                dataset_scope=dataset_scope,
                evaluation_version=EVALUATION_VERSION,
            )
            continue

        mae = round(sum(abs(e) for e in errors) / count, 2)
        rmse = round(math.sqrt(sum(e**2 for e in errors) / count), 2)
        inside_count = sum(1 for w in horizon_within_intervals[h] if w)
        coverage_pct = round((inside_count / count) * 100.0, 1)

        summaries[h] = EvaluationSummary(
            horizon_minutes=h,
            sample_count=count,
            mae_mps=mae,
            rmse_mps=rmse,
            interval_coverage_pct=coverage_pct,
            dataset_scope=dataset_scope,
            evaluation_version=EVALUATION_VERSION,
        )

    metadata = {
        "total_predictions": len(predictions),
        "evaluated_count": evaluated_count,
        "abstained_count": abstained_count,
        "missing_actual_count": missing_actual_count,
        "evaluation_version": EVALUATION_VERSION,
        "evaluated_at": eval_utc.isoformat(),
    }

    return evaluations, summaries, metadata
