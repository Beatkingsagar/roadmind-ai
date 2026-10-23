"""Administrative endpoints for operator demonstrations and data seeding."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, verify_reviewer_auth
from pipelines.ingest.seed import seed_database

router = APIRouter(tags=["Admin & Seeding"])


@router.post(
    "/admin/seed",
    summary="Seed or safely reset SQLite database from deterministic fixtures (Protected)",
)
@router.post(
    "/seed",
    include_in_schema=False,
)
def run_database_seed(
    reset: bool = Query(False, description="If True, drop and recreate tables before seeding"),
    operator_role: str = Depends(verify_reviewer_auth),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Idempotently seed database from verified fixture files."""
    counts = seed_database(db, reset=reset)
    return {
        "status": "success",
        "action": "reset_and_seed" if reset else "idempotent_seed",
        "counts": counts,
    }
