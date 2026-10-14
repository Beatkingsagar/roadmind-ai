"""Database engine and session management for RoadMind AI.

Configures SQLite with thread safety, foreign key constraints,
and session generator dependency for FastAPI.
"""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

# Configure SQLite engine with foreign keys enabled
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    future=True,
)

# SQLite pragma to enforce foreign key constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined on Base metadata."""
    # Import all models to ensure they are registered on Base
    import backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Drop and recreate all database tables (development/testing only)."""
    import backend.app.models  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
