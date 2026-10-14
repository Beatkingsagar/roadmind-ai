"""Data source provenance and licensing model."""

from __future__ import annotations

from sqlalchemy import Column, String, Text
from backend.app.database import Base
from backend.app.models.base import UTCDateTime, utc_now


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    origin = Column(String(256), nullable=False)
    license_status = Column(String(128), nullable=False)
    geography = Column(String(128), nullable=False)
    coverage = Column(String(256), nullable=False)
    retrieval_time = Column(UTCDateTime, default=utc_now, nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA-256
    limitations = Column(Text, nullable=False)
    data_mode = Column(String(32), default="synthetic", nullable=False)  # synthetic, historical, user_submitted

    def __repr__(self) -> str:
        return f"<DataSource id={self.id} name={self.name} mode={self.data_mode}>"
