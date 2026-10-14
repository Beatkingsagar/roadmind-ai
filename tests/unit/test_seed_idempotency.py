"""Unit tests verifying database seed idempotency and manifest SHA-256 integrity."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Bootstrap local packages into sys.path
_workspace = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

import pytest
from backend.app.config import settings
from backend.app.database import SessionLocal, reset_db
from backend.app.models import (
    DataSource,
    Evidence,
    IncidentEpisode,
    IncidentReview,
    Observation,
    OutcomeEvaluation,
    Prediction,
    Report,
    RoadSegment,
)
from pipelines.ingest.seed import seed_database, verify_manifest


def test_manifest_checksum_integrity():
    """Verify that all fixture files on disk match the recorded SHA-256 checksums in manifest.json."""
    assert verify_manifest() is True


def test_seed_database_idempotency():
    """Verify that running seed_database twice does not duplicate any rows."""
    session = SessionLocal()
    try:
        # First pass: seed into clean DB
        reset_db()
        first_run = seed_database(session, reset=False)
        assert first_run["road_segments"] > 0
        assert first_run["observations"] > 0
        assert first_run["reports"] > 0

        # Snapshot counts
        count_segments = session.query(RoadSegment).count()
        count_obs = session.query(Observation).count()
        count_reps = session.query(Report).count()
        count_evs = session.query(Evidence).count()
        count_eps = session.query(IncidentEpisode).count()
        count_preds = session.query(Prediction).count()

        # Second pass: re-run seed without reset
        second_run = seed_database(session, reset=False)
        for entity, added in second_run.items():
            assert added == 0, f"Entity '{entity}' added {added} unexpected duplicate records on second run!"

        # Counts must be identical
        assert session.query(RoadSegment).count() == count_segments
        assert session.query(Observation).count() == count_obs
        assert session.query(Report).count() == count_reps
        assert session.query(Evidence).count() == count_evs
        assert session.query(IncidentEpisode).count() == count_eps
        assert session.query(Prediction).count() == count_preds
    finally:
        session.close()
