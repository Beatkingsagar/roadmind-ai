"""Speed forecasting and chronological outcome evaluation API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, parse_temporal_at
from backend.app.models import Observation, Prediction, RoadSegment
from backend.app.schemas.prediction import PredictionResponse
from backend.app.services.forecasting.engine import (
    evaluate_chronological_predictions,
    generate_historical_median_forecast,
    generate_persistence_forecast,
)
from backend.app.services.replay.filter import (
    ensure_utc,
    filter_eligible_observations,
)

router = APIRouter(tags=["Forecasting & Evaluations"])


@router.get(
    "/forecasts",
    response_model=PredictionResponse,
    summary="Generate a baseline speed forecast with explicit abstention guarantees",
)
@router.get(
    "/forecasting/predict",
    response_model=PredictionResponse,
    include_in_schema=False,
)
def get_forecast(
    segment_id: str = Query(..., description="Target road segment ID"),
    at: datetime = Depends(parse_temporal_at),
    horizon_minutes: int = Query(15, ge=5, le=120, description="Forecast horizon in minutes (e.g. 15 or 30)"),
    model_type: str = Query(
        "persistence",
        description="Forecast model type: 'persistence' or 'historical_median'",
    ),
    persist: bool = Query(
        False,
        description="If True, persists the newly computed prediction record in the database",
    ),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    """Generate deterministic speed prediction.

    Guarantees:
    - Never uses observations where available_at > 'at'.
    - Abstains with explicit reason (e.g. INSUFFICIENT_HISTORY, STALE_OBSERVATIONS)
      rather than fabricating non-existent traffic forecasts.
    """
    segment = db.query(RoadSegment).filter(RoadSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road segment '{segment_id}' not found.",
        )

    t_issue = ensure_utc(at)

    # Strictly filter observations up to issue time
    eligible_obs = filter_eligible_observations(db, replay_time=t_issue)

    normalized_model = model_type.strip().lower()
    if normalized_model == "historical_median":
        pred_response = generate_historical_median_forecast(
            observations=eligible_obs,
            segment_id=segment_id,
            issue_time=t_issue,
            horizon_minutes=horizon_minutes,
        )
    elif normalized_model == "persistence":
        pred_response = generate_persistence_forecast(
            observations=eligible_obs,
            segment_id=segment_id,
            issue_time=t_issue,
            horizon_minutes=horizon_minutes,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported model_type '{model_type}'. Choose 'persistence' or 'historical_median'.",
        )

    if persist:
        prediction_db = Prediction(
            id=pred_response.id,
            segment_id=segment_id,
            issue_time=pred_response.issue_time,
            target_time=pred_response.target_time,
            horizon_minutes=pred_response.horizon_minutes,
            model_version=pred_response.model_version,
            input_snapshot_reference=pred_response.input_snapshot_reference,
            predicted_speed_mps=pred_response.predicted_speed_mps,
            interval_lower_mps=pred_response.interval_lower_mps,
            interval_upper_mps=pred_response.interval_upper_mps,
            confidence_level=pred_response.confidence_level,
            abstention_reason=pred_response.abstention_reason.value if pred_response.abstention_reason else None,
            data_mode="synthetic",
        )
        db.add(prediction_db)
        db.commit()

    return pred_response


@router.get(
    "/evaluations",
    summary="Chronologically evaluate stored predictions against revealed actual observations",
)
@router.get(
    "/forecasting/evaluate",
    include_in_schema=False,
)
def get_evaluations(
    at: datetime = Depends(parse_temporal_at),
    horizon_minutes: Optional[int] = Query(None, description="Optional horizon filter (15 or 30)"),
    tolerance_minutes: int = Query(5, ge=1, le=30, description="Temporal alignment tolerance in minutes"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Perform chronological outcome evaluation of forecasts.

    Guarantees:
    - Never evaluates against actual observations whose available_at > 'at'.
    - Previously stored predictions are never modified.
    - Abstaining predictions are not scored into error metrics, but counted transparently.
    """
    t_eval = ensure_utc(at)

    # 1. Query predictions issued at or before evaluation cutoff
    pred_query = db.query(Prediction).filter(Prediction.issue_time <= t_eval)
    if horizon_minutes is not None:
        pred_query = pred_query.filter(Prediction.horizon_minutes == horizon_minutes)
    predictions = pred_query.all()

    # 2. Query eligible observations available at or before evaluation cutoff
    observations = filter_eligible_observations(db, replay_time=t_eval)

    # 3. Chronological evaluation
    individual_evals, summaries, counts = evaluate_chronological_predictions(
        predictions=predictions,
        observations=observations,
        evaluation_time=t_eval,
        tolerance_minutes=tolerance_minutes,
    )

    return {
        "evaluation_time": t_eval.isoformat(),
        "tolerance_minutes": tolerance_minutes,
        "sample_metrics": counts,
        "horizon_summaries": {str(k): v.model_dump(mode="json") for k, v in summaries.items()},
        "evaluations": [e.model_dump(mode="json") for e in individual_evals],
    }
