"""Evidence model with server-side SHA-256 duplicate detection and private storage reference."""

from __future__ import annotations

import json
from typing import Any, Dict
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(64), primary_key=True)
    report_id = Column(String(64), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Server-calculated SHA-256 hash of media bytes
    content_hash = Column(String(64), nullable=False, index=True)
    storage_path = Column(String(512), nullable=False)  # Stored in private directory outside web root
    media_type = Column(String(64), default="image/jpeg", nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    
    # Untrusted client metadata claims (EXIF, camera reported timestamps)
    metadata_claims_json = Column(Text, default="{}", nullable=False)
    
    # Deduplication tracking: reused bytes must not provide independent corroboration
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_id = Column(String(64), ForeignKey("evidence.id"), nullable=True)
    perceptual_hash = Column(String(64), nullable=True)
    
    submitted_at = Column(UTCDateTime, default=utc_now, nullable=False)
    available_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    report = relationship("Report", back_populates="evidence_items")
    duplicate_of = relationship("Evidence", remote_side=[id])

    @property
    def metadata_claims(self) -> Dict[str, Any]:
        """Parsed dictionary of client claims."""
        try:
            return json.loads(self.metadata_claims_json)
        except Exception:
            return {}

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} hash={self.content_hash[:8]} is_dup={self.is_duplicate}>"
