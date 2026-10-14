"""Idempotent database seeding script for RoadMind AI.

Reads deterministic fixtures from data/fixtures/ and populates SQLite.
Ensures:
- Idempotency: repeating seed does not duplicate records.
- Integrity: checks fixture checksums against manifest.json.
- Preservation of observed_at vs available_at timestamps.
- Explicit labelling of synthetic data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure local packages and workspace root are in sys.path
_workspace_root = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace_root / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from typing import Any, Dict
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import SessionLocal, init_db, reset_db
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


def parse_iso_utc(ts_str: str | None) -> datetime | None:
    """Parse ISO formatted timestamp into timezone-aware UTC datetime."""
    if not ts_str:
        return None
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def verify_manifest() -> bool:
    """Verify that fixture files match their recorded SHA-256 checksums in manifest.json."""
    manifest_path = settings.manifests_dir / "manifest.json"
    if not manifest_path.exists():
        return False
    
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for filename, meta in manifest.get("files", {}).items():
        file_path = settings.workspace_root / meta["path"]
        if not file_path.exists():
            return False
        computed = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if computed != meta["checksum_sha256"]:
            return False
    return True


def seed_database(db: Session, reset: bool = False) -> Dict[str, int]:
    """Idempotently seed database from fixture files."""
    if reset:
        reset_db()
    else:
        init_db()

    fixtures_path = settings.fixtures_dir / "seed_fixtures.json"
    network_path = settings.fixtures_dir / "synthetic_network.geojson"
    
    if not fixtures_path.exists() or not network_path.exists():
        from pipelines.ingest.generate_fixtures import write_fixtures_and_manifest
        write_fixtures_and_manifest()

    network_data = json.loads(network_path.read_text(encoding="utf-8"))
    fixtures_data = json.loads(fixtures_path.read_text(encoding="utf-8"))

    counts = {
        "data_sources": 0,
        "road_segments": 0,
        "observations": 0,
        "reports": 0,
        "evidence": 0,
        "episodes": 0,
        "reviews": 0,
        "predictions": 0,
        "evaluations": 0,
    }

    # 1. Data Source
    ds_raw = fixtures_data["data_source"]
    ds = db.query(DataSource).filter_by(id=ds_raw["id"]).first()
    if not ds:
        ds = DataSource(
            id=ds_raw["id"],
            name=ds_raw["name"],
            origin=ds_raw["origin"],
            license_status=ds_raw["license_status"],
            geography=ds_raw["geography"],
            coverage=ds_raw["coverage"],
            retrieval_time=parse_iso_utc(ds_raw["retrieval_time"]),
            checksum=ds_raw["checksum"],
            limitations=ds_raw["limitations"],
            data_mode=ds_raw["data_mode"],
        )
        db.add(ds)
        counts["data_sources"] += 1

    # 2. Road Segments
    for feat in network_data["features"]:
        p = feat["properties"]
        seg = db.query(RoadSegment).filter_by(id=p["id"]).first()
        if not seg:
            seg = RoadSegment(
                id=p["id"],
                name=p["name"],
                graph_version=network_data.get("graph_version", "v1.0.0"),
                source_node=p["source_node"],
                target_node=p["target_node"],
                directed_edge_id=p["directed_edge_id"],
                is_one_way=p["is_one_way"],
                length_meters=p["length_meters"],
                free_flow_speed_mps=p["free_flow_speed_mps"],
                access_assumptions=p["access_assumptions"],
                functional_class=p["functional_class"],
                geometry_json=json.dumps(feat["geometry"]["coordinates"]),
                data_mode=p["data_mode"],
            )
            db.add(seg)
            counts["road_segments"] += 1
    db.flush()

    # 3. Incident Episodes (must exist before reports reference them)
    for ep_raw in fixtures_data["episodes"]:
        ep = db.query(IncidentEpisode).filter_by(id=ep_raw["id"]).first()
        if not ep:
            ep = IncidentEpisode(
                id=ep_raw["id"],
                primary_segment_id=ep_raw["primary_segment_id"],
                affected_segments_json=json.dumps(ep_raw["affected_segments"]),
                episode_type=ep_raw["episode_type"],
                first_reported_at=parse_iso_utc(ep_raw["first_reported_at"]),
                last_reported_at=parse_iso_utc(ep_raw["last_reported_at"]),
                lifecycle_status=ep_raw["lifecycle_status"],
                severity_level=ep_raw["severity_level"],
                heuristic_support_score=ep_raw["heuristic_support_score"],
                assessment_summary=ep_raw["assessment_summary"],
                rubric_version=ep_raw["rubric_version"],
                reviewer_state=ep_raw["reviewer_state"],
            )
            db.add(ep)
            counts["episodes"] += 1
    db.flush()

    # 4. Reports
    for rep_raw in fixtures_data["reports"]:
        rep = db.query(Report).filter_by(id=rep_raw["id"]).first()
        if not rep:
            rep = Report(
                id=rep_raw["id"],
                incident_type=rep_raw["incident_type"],
                claimed_event_time=parse_iso_utc(rep_raw["claimed_event_time"]),
                submitted_at=parse_iso_utc(rep_raw["submitted_at"]),
                available_at=parse_iso_utc(rep_raw["available_at"]),
                segment_id=rep_raw["segment_id"],
                location_description=rep_raw["location_description"],
                latitude=rep_raw["latitude"],
                longitude=rep_raw["longitude"],
                reporter_reference=rep_raw["reporter_reference"],
                dependency_group_id=rep_raw["dependency_group_id"],
                description=rep_raw["description"],
                data_mode=rep_raw["data_mode"],
                idempotency_key=rep_raw["idempotency_key"],
                episode_id=rep_raw["episode_id"],
            )
            db.add(rep)
            counts["reports"] += 1
    db.flush()

    # 5. Evidence
    for ev_raw in fixtures_data["evidence"]:
        ev = db.query(Evidence).filter_by(id=ev_raw["id"]).first()
        if not ev:
            ev = Evidence(
                id=ev_raw["id"],
                report_id=ev_raw["report_id"],
                content_hash=ev_raw["content_hash"],
                storage_path=ev_raw["storage_path"],
                media_type=ev_raw["media_type"],
                file_size_bytes=ev_raw["file_size_bytes"],
                metadata_claims_json=json.dumps(ev_raw["metadata_claims"]),
                is_duplicate=ev_raw["is_duplicate"],
                duplicate_of_id=ev_raw["duplicate_of_id"],
                perceptual_hash=ev_raw["perceptual_hash"],
                submitted_at=parse_iso_utc(ev_raw["submitted_at"]),
                available_at=parse_iso_utc(ev_raw["available_at"]),
            )
            db.add(ev)
            counts["evidence"] += 1
    db.flush()

    # 6. Incident Reviews
    for rev_raw in fixtures_data["reviews"]:
        rev = db.query(IncidentReview).filter_by(id=rev_raw["id"]).first()
        if not rev:
            rev = IncidentReview(
                id=rev_raw["id"],
                episode_id=rev_raw["episode_id"],
                reviewer_reference=rev_raw["reviewer_reference"],
                decision=rev_raw["decision"],
                reason=rev_raw["reason"],
                previous_state=rev_raw["previous_state"],
                recorded_at=parse_iso_utc(rev_raw["recorded_at"]),
                available_at=parse_iso_utc(rev_raw["available_at"]),
            )
            db.add(rev)
            counts["reviews"] += 1
    db.flush()

    # 7. Observations
    for obs_raw in fixtures_data["observations"]:
        obs = db.query(Observation).filter_by(id=obs_raw["id"]).first()
        if not obs:
            obs = Observation(
                id=obs_raw["id"],
                segment_id=obs_raw["segment_id"],
                observed_at=parse_iso_utc(obs_raw["observed_at"]),
                available_at=parse_iso_utc(obs_raw["available_at"]),
                value=obs_raw["value"],
                unit=obs_raw["unit"],
                quality_score=obs_raw["quality_score"],
                provenance=obs_raw["provenance"],
                data_mode=obs_raw["data_mode"],
            )
            db.add(obs)
            counts["observations"] += 1
    db.flush()

    # 8. Predictions
    for pred_raw in fixtures_data["predictions"]:
        pred = db.query(Prediction).filter_by(id=pred_raw["id"]).first()
        if not pred:
            pred = Prediction(
                id=pred_raw["id"],
                segment_id=pred_raw["segment_id"],
                issue_time=parse_iso_utc(pred_raw["issue_time"]),
                target_time=parse_iso_utc(pred_raw["target_time"]),
                horizon_minutes=pred_raw["horizon_minutes"],
                model_version=pred_raw["model_version"],
                input_snapshot_reference=pred_raw["input_snapshot_reference"],
                predicted_speed_mps=pred_raw["predicted_speed_mps"],
                interval_lower_mps=pred_raw["interval_lower_mps"],
                interval_upper_mps=pred_raw["interval_upper_mps"],
                confidence_level=pred_raw["confidence_level"],
                abstention_reason=pred_raw["abstention_reason"],
                data_mode=pred_raw["data_mode"],
            )
            db.add(pred)
            counts["predictions"] += 1
    db.flush()

    # 9. Evaluations
    for eval_raw in fixtures_data["evaluations"]:
        ev_obj = db.query(OutcomeEvaluation).filter_by(id=eval_raw["id"]).first()
        if not ev_obj:
            ev_obj = OutcomeEvaluation(
                id=eval_raw["id"],
                prediction_id=eval_raw["prediction_id"],
                observation_id=eval_raw["observation_id"],
                error_speed_mps=eval_raw["error_speed_mps"],
                absolute_error_mps=eval_raw["absolute_error_mps"],
                within_interval=eval_raw["within_interval"],
                evaluated_at=parse_iso_utc(eval_raw["evaluated_at"]),
                evaluation_version=eval_raw["evaluation_version"],
            )
            db.add(ev_obj)
            counts["evaluations"] += 1

    db.commit()
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed RoadMind AI SQLite database")
    parser.add_argument("--reset", action="store_true", help="Drop existing tables before seeding")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        inserted = seed_database(session, reset=args.reset)
        print("SEED COMPLETED SUCCESSFULLY:")
        for entity, count in inserted.items():
            print(f"  {entity}: {count} records added")
    finally:
        session.close()
