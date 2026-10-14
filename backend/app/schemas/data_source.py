"""Data source Pydantic contracts."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import DataMode


class DataSourceBase(BaseModel):
    name: str
    origin: str
    license_status: str
    geography: str
    coverage: str
    checksum: str
    limitations: str
    data_mode: DataMode = DataMode.SYNTHETIC


class DataSourceCreate(DataSourceBase):
    id: str


class DataSourceResponse(DataSourceBase):
    id: str
    retrieval_time: datetime

    model_config = ConfigDict(from_attributes=True)
