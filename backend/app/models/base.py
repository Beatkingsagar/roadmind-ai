"""Base definitions, custom types, and mixins for SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, TypeDecorator
from backend.app.database import Base


class UTCDateTime(TypeDecorator):
    """DateTime type that always stores and returns timezone-aware UTC datetimes."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                # Assume naive datetime is UTC
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)
