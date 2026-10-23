"""Network and road state API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, parse_temporal_at
from backend.app.config import settings
from backend.app.models import IncidentEpisode, Observation, Report, RoadSegment
from backend.app.schemas.common import DataMode
from backend.app.schemas.memory import SegmentMemorySummary
from backend.app.schemas.observation import ObservationResponse
from backend.app.schemas.road_network import (
    NetworkGeoJSONResponse,
    RoadSegmentResponse,
    RoadStateSnapshot,
)
from backend.app.services.memory.road_memory import build_segment_memory_summaries
from backend.app.services.replay.filter import (
    ensure_utc,
    filter_eligible_observations,
    filter_eligible_reports,
)

router = APIRouter(tags=["Network & Road State"])


@router.get(
    "/network",
    response_model=NetworkGeoJSONResponse,
    summary="Get complete road network as GeoJSON FeatureCollection",
)
@router.get(
    "/network/geojson",
    response_model=NetworkGeoJSONResponse,
    include_in_schema=False,
)
def get_network_geojson(db: Session = Depends(get_db)) -> NetworkGeoJSONResponse:
    """Retrieve full road network vector geometry and properties."""
    segments = db.query(RoadSegment).all()
    features = [seg.to_geojson_feature() for seg in segments]

    return NetworkGeoJSONResponse(
        type="FeatureCollection",
        graph_version=settings.graph_version,
        data_mode=DataMode.SYNTHETIC,
        attribution="RoadMind AI — NEXATHON 2026 Traffic Intelligence Track",
        features=features,
    )


@router.get(
    "/network/segments",
    response_model=List[RoadSegmentResponse],
    summary="List all road segments with topology and speed specifications",
)
def list_road_segments(db: Session = Depends(get_db)) -> List[RoadSegmentResponse]:
    """List all configured road network segments."""
    segments = db.query(RoadSegment).all()
    return [RoadSegmentResponse.model_validate(seg) for seg in segments]


@router.get(
    "/road-state",
    response_model=List[RoadStateSnapshot],
    summary="Get dynamic road state snapshots filtered by temporal replay time",
)
@router.get(
    "/replay/state",
    response_model=List[RoadStateSnapshot],
    include_in_schema=False,
)
def get_road_state(
    at: datetime = Depends(parse_temporal_at),
    db: Session = Depends(get_db),
) -> List[RoadStateSnapshot]:
    """Retrieve dynamic road state snapshot for all network segments.

    Enforces temporal eligibility: only observations available at or before 'at'
    are incorporated. If no observations exist, falls back to free-flow baseline
    with clear provenance.
    """
    t_replay = ensure_utc(at)
    segments = db.query(RoadSegment).all()

    # Query all eligible observations up to replay time
    eligible_obs = filter_eligible_observations(db, replay_time=t_replay)
    obs_by_segment: Dict[str, List[Observation]] = {}
    for o in eligible_obs:
        obs_by_segment.setdefault(o.segment_id, []).append(o)

    snapshots: List[RoadStateSnapshot] = []

    for seg in segments:
        seg_obs = obs_by_segment.get(seg.id, [])
        latest_obs: Optional[Observation] = None
        if seg_obs:
            latest_obs = max(seg_obs, key=lambda x: ensure_utc(x.observed_at))

        if latest_obs:
            current_mps = round(latest_obs.speed_mps, 2)
            obs_time_str = ensure_utc(latest_obs.observed_at).isoformat()
            freshness_sec = max(
                0.0,
                round((t_replay - ensure_utc(latest_obs.observed_at)).total_seconds(), 1),
            )
            provenance_val = latest_obs.provenance
        else:
            current_mps = round(seg.free_flow_speed_mps, 2)
            obs_time_str = None
            freshness_sec = None
            provenance_val = "free_flow_baseline"

        congestion = round(current_mps / seg.free_flow_speed_mps, 2)

        # Count active incidents on this segment as of replay time
        active_count = (
            db.query(IncidentEpisode)
            .filter(
                IncidentEpisode.primary_segment_id == seg.id,
                IncidentEpisode.first_reported_at <= t_replay,
                IncidentEpisode.lifecycle_status != "resolved",
            )
            .count()
        )

        snapshots.append(
            RoadStateSnapshot(
                segment_id=seg.id,
                name=seg.name,
                source_node=seg.source_node,
                target_node=seg.target_node,
                current_speed_mps=current_mps,
                current_speed_kmph=round(current_mps * 3.6, 2),
                free_flow_speed_mps=seg.free_flow_speed_mps,
                congestion_ratio=congestion,
                active_incidents_count=active_count,
                latest_observation_time=obs_time_str,
                observation_freshness_seconds=freshness_sec,
                provenance=provenance_val,
                data_mode=DataMode(seg.data_mode) if seg.data_mode in DataMode.__members__.values() else DataMode.SYNTHETIC,
            )
        )

    return snapshots


@router.get(
    "/segments/{id}/history",
    summary="Get detailed historical observations, reports, and memory summary for a road segment",
)
def get_segment_history(
    id: str,
    at: datetime = Depends(parse_temporal_at),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full historical profile of a road segment.

    Includes replay-filtered observations, reports, and spatiotemporal memory summary.
    """
    segment = db.query(RoadSegment).filter(RoadSegment.id == id).first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road segment with id '{id}' not found.",
        )

    t_replay = ensure_utc(at)
    obs = filter_eligible_observations(db, segment_id=id, replay_time=t_replay)
    reports = filter_eligible_reports(db, segment_id=id, replay_time=t_replay)

    summaries = build_segment_memory_summaries(
        segments=[segment],
        reports=reports,
        observations=obs,
        replay_time=t_replay,
    )
    seg_summary = summaries[0] if summaries else None

    # Return latest 20 observations chronologically descending for inspection
    recent_obs = sorted(obs, key=lambda x: ensure_utc(x.observed_at), reverse=True)[:20]

    return {
        "segment": RoadSegmentResponse.model_validate(segment).model_dump(mode="json"),
        "replay_time": t_replay.isoformat(),
        "total_observations_eligible": len(obs),
        "total_reports_eligible": len(reports),
        "memory_summary": seg_summary.model_dump(mode="json") if seg_summary else None,
        "recent_observations": [
            ObservationResponse.model_validate(o).model_dump(mode="json") for o in recent_obs
        ],
    }
