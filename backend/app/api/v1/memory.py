"""Road memory and transparent inspection priority ranking endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, parse_temporal_at
from backend.app.models import RoadSegment
from backend.app.schemas.memory import InspectionPriority
from backend.app.services.memory.road_memory import (
    build_segment_memory_summaries,
    rank_inspection_priorities,
)
from backend.app.services.replay.filter import (
    ensure_utc,
    filter_eligible_observations,
    filter_eligible_reports,
)

router = APIRouter(tags=["Road Memory & Inspection Priorities"])


@router.get(
    "/memory/priority",
    response_model=List[InspectionPriority],
    summary="Get transparent, explainable road segment inspection priority rankings",
)
@router.get(
    "/memory/inspection-priority",
    response_model=List[InspectionPriority],
    include_in_schema=False,
)
def get_inspection_priorities(
    at: datetime = Depends(parse_temporal_at),
    db: Session = Depends(get_db),
) -> List[InspectionPriority]:
    """Rank road segments by inspection priority under temporal replay.

    Methodology:
    - Clusters raw reports into distinct spatiotemporal episodes (duplicates do not inflate count).
    - Checks observation coverage density: flags poor coverage so lack of reports
      is not mistaken for safe conditions.
    - Uses transparent inspection rubric ('inspection_v1.0') providing full factor breakdown.
    """
    t_replay = ensure_utc(at)
    segments = db.query(RoadSegment).all()

    # Replay-eligible inputs
    observations = filter_eligible_observations(db, replay_time=t_replay)
    reports = filter_eligible_reports(db, replay_time=t_replay)

    summaries = build_segment_memory_summaries(
        segments=segments,
        reports=reports,
        observations=observations,
        replay_time=t_replay,
    )

    priorities = rank_inspection_priorities(summaries)
    return priorities
