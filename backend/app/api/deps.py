"""FastAPI common dependencies for RoadMind AI API.

Provides:
- Database session injection.
- Replay timestamp parsing with timezone normalization.
- Reviewer authorization boundary enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from fastapi import Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.services.replay.filter import ensure_utc


def parse_temporal_at(
    at: Optional[str] = Query(
        None,
        description="Temporal replay cutoff timestamp in ISO-8601 format (e.g. '2026-10-23T08:30:00Z'). Defaults to current UTC.",
    ),
) -> datetime:
    """Parse and normalize optional temporal replay parameter."""
    if not at:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(at.replace("Z", "+00:00"))
        return ensure_utc(dt)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO timestamp format for 'at': '{at}'. Expected ISO-8601 (e.g. 2026-10-23T08:30:00Z).",
        ) from exc


def verify_reviewer_auth(
    x_reviewer_role: Optional[str] = Header(None, alias="X-Reviewer-Role"),
    x_reviewer_token: Optional[str] = Header(None, alias="X-Reviewer-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """Enforces reviewer authorization boundary.

    Guards review actions so public users cannot verify or alter incident states.
    Accepts:
    1. 'X-Reviewer-Role' header with a recognized operator role.
    2. 'X-Reviewer-Token' matching settings.operator_token.
    3. 'Authorization: Bearer <token>' matching settings.operator_token.

    Raises:
        HTTPException(403) if authorization fails.
    """
    authorized_roles = {"traffic_operator", "traffic_supervisor", "admin", "system_evaluator"}

    if x_reviewer_role and x_reviewer_role.strip().lower() in authorized_roles:
        return x_reviewer_role.strip().lower()

    if x_reviewer_token and x_reviewer_token.strip() == settings.operator_token:
        return "traffic_operator"

    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == settings.operator_token:
            return "traffic_operator"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Reviewer authorization required. Only verified traffic operators can submit incident reviews. "
            "Please provide 'X-Reviewer-Role: traffic_operator' or a valid 'X-Reviewer-Token' header."
        ),
    )
