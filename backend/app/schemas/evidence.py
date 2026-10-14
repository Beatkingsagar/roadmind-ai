"""Evidence schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    id: str
    report_id: str
    content_hash: str
    media_type: str
    file_size_bytes: int
    metadata_claims: Dict[str, Any]
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    perceptual_hash: Optional[str] = None
    submitted_at: datetime
    available_at: datetime

    model_config = ConfigDict(from_attributes=True)
