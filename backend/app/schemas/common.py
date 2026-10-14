"""Common Pydantic types, enums, and response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class DataMode(str, Enum):
    SYNTHETIC = "synthetic"
    HISTORICAL = "historical"
    USER_SUBMITTED = "user_submitted"


class IncidentType(str, Enum):
    ACCIDENT = "accident"
    POTHOLE = "pothole"
    ROAD_DAMAGE = "road_damage"
    DEBRIS = "debris"
    FLOODING = "flooding"
    STALL = "stall"


class ReviewDecision(str, Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_INVESTIGATION = "needs_investigation"


class SensitivityOutcome(str, Enum):
    ROBUST_ALTERNATIVE = "ROBUST_ALTERNATIVE"
    EVIDENCE_SENSITIVE = "EVIDENCE_SENSITIVE"
    NO_ROUTE_AVAILABLE = "NO_ROUTE_AVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AbstentionReason(str, Enum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    STALE_OBSERVATIONS = "STALE_OBSERVATIONS"
    UNOBSERVED_SEGMENT = "UNOBSERVED_SEGMENT"
    INVALID_UNITS = "INVALID_UNITS"


class StandardResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    replay_time: Optional[datetime] = None
    data_mode: DataMode = DataMode.SYNTHETIC


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    status: str = "error"
    error: ErrorDetail
