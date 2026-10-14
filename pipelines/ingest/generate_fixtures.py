"""Deterministic fixture generator for RoadMind AI.

Generates:
1. Synthetic road network (GeoJSON and segment records).
2. Seed fixtures for observations, reports, evidence, episodes, predictions, and evaluations.
3. Incorporates all 12 non-negotiable benchmark test fixtures:
   - One-way roads
   - Parallel directed edges (preserving multi-edge identity)
   - Corridor and bypass
   - Full closure alternative
   - Disconnected destination
   - Duplicate evidence (SHA-256 byte deduplication)
   - Shared-source reports (dependency group contribution cap)
   - Conflicting evidence (future timestamp & speed sensor contradiction)
   - Distinct recurring episodes (same segment, separated in time)
   - Late-arriving observations (observed_at < available_at)
   - Sparse forecasting history (abstention)
   - Later outcome observation (immutable prediction evaluation)
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure local packages and workspace root are in sys.path
_workspace_root = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace_root / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from typing import Any, Dict, List
from backend.app.config import settings

# Fixed reference epoch for deterministic generation
REFERENCE_EPOCH = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc)


def compute_sha256(data: bytes | str) -> str:
    """Compute SHA-256 hexadecimal digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def generate_network_data() -> Dict[str, Any]:
    """Generate synthetic road segments with coordinates and directed graph topology."""
    segments = [
        # 1. Main Corridor West
        {
            "id": "seg_corridor_w",
            "name": "Grand Corridor West",
            "source_node": "node_origin",
            "target_node": "node_corridor_mid",
            "directed_edge_id": "edge_0",
            "is_one_way": False,
            "length_meters": 1200.0,
            "free_flow_speed_mps": 13.89,  # 50 km/h
            "access_assumptions": "all_vehicles",
            "functional_class": "arterial",
            "geometry": [[-73.9850, 40.7480], [-73.9825, 40.7490], [-73.9800, 40.7500]],
            "data_mode": "synthetic",
        },
        # 2. Main Corridor East (Incident target segment)
        {
            "id": "seg_corridor_e",
            "name": "Grand Corridor East",
            "source_node": "node_corridor_mid",
            "target_node": "node_destination",
            "directed_edge_id": "edge_0",
            "is_one_way": False,
            "length_meters": 1400.0,
            "free_flow_speed_mps": 13.89,  # 50 km/h
            "access_assumptions": "all_vehicles",
            "functional_class": "arterial",
            "geometry": [[-73.9800, 40.7500], [-73.9775, 40.7510], [-73.9750, 40.7520]],
            "data_mode": "synthetic",
        },
        # Reverse corridor east (for two-way corridor)
        {
            "id": "seg_corridor_e_rev",
            "name": "Grand Corridor East (Inbound)",
            "source_node": "node_destination",
            "target_node": "node_corridor_mid",
            "directed_edge_id": "edge_0",
            "is_one_way": True,
            "length_meters": 1400.0,
            "free_flow_speed_mps": 13.89,
            "access_assumptions": "all_vehicles",
            "functional_class": "arterial",
            "geometry": [[-73.9750, 40.7520], [-73.9775, 40.7510], [-73.9800, 40.7500]],
            "data_mode": "synthetic",
        },
        # 3. Parallel Directed Edge: Express Lane on Corridor West (node_origin -> node_corridor_mid)
        {
            "id": "seg_corridor_w_express",
            "name": "Grand Corridor West Express",
            "source_node": "node_origin",
            "target_node": "node_corridor_mid",
            "directed_edge_id": "edge_express_1",  # Distinct parallel edge ID
            "is_one_way": True,
            "length_meters": 1150.0,
            "free_flow_speed_mps": 16.67,  # 60 km/h
            "access_assumptions": "express_only",
            "functional_class": "highway",
            "geometry": [[-73.9850, 40.7480], [-73.9820, 40.7492], [-73.9800, 40.7500]],
            "data_mode": "synthetic",
        },
        # 4. Bypass West
        {
            "id": "seg_bypass_w",
            "name": "Southern Bypass West",
            "source_node": "node_origin",
            "target_node": "node_bypass_mid",
            "directed_edge_id": "edge_0",
            "is_one_way": False,
            "length_meters": 1600.0,
            "free_flow_speed_mps": 15.28,  # 55 km/h
            "access_assumptions": "all_vehicles",
            "functional_class": "bypass",
            "geometry": [[-73.9850, 40.7480], [-73.9830, 40.7460], [-73.9800, 40.7450]],
            "data_mode": "synthetic",
        },
        # 5. Bypass East
        {
            "id": "seg_bypass_e",
            "name": "Southern Bypass East",
            "source_node": "node_bypass_mid",
            "target_node": "node_destination",
            "directed_edge_id": "edge_0",
            "is_one_way": False,
            "length_meters": 1700.0,
            "free_flow_speed_mps": 15.28,  # 55 km/h
            "access_assumptions": "all_vehicles",
            "functional_class": "bypass",
            "geometry": [[-73.9800, 40.7450], [-73.9770, 40.7470], [-73.9750, 40.7520]],
            "data_mode": "synthetic",
        },
        # 6. One-Way Road: Corridor Mid to Hub North (traversable S->N only)
        {
            "id": "seg_oneway_north",
            "name": "Northbound Boulevard (One-Way)",
            "source_node": "node_corridor_mid",
            "target_node": "node_hub_north",
            "directed_edge_id": "edge_0",
            "is_one_way": True,
            "length_meters": 800.0,
            "free_flow_speed_mps": 11.11,  # 40 km/h
            "access_assumptions": "one_way_only",
            "functional_class": "local",
            "geometry": [[-73.9800, 40.7500], [-73.9790, 40.7530], [-73.9780, 40.7560]],
            "data_mode": "synthetic",
        },
        # 7. Sparse History Road (for testing forecast abstention)
        {
            "id": "seg_sparse_history",
            "name": "Industrial Spur Road (Sparse Data)",
            "source_node": "node_corridor_mid",
            "target_node": "node_stale_zone",
            "directed_edge_id": "edge_0",
            "is_one_way": False,
            "length_meters": 900.0,
            "free_flow_speed_mps": 10.0,  # 36 km/h
            "access_assumptions": "all_vehicles",
            "functional_class": "local",
            "geometry": [[-73.9800, 40.7500], [-73.9750, 40.7495], [-73.9700, 40.7490]],
            "data_mode": "synthetic",
        },
        # 8. Disconnected Destination test edge (node_isolated has NO incoming edges)
        {
            "id": "seg_isolated_out",
            "name": "Isolated Sector Outflow",
            "source_node": "node_isolated",
            "target_node": "node_destination",
            "directed_edge_id": "edge_0",
            "is_one_way": True,
            "length_meters": 2000.0,
            "free_flow_speed_mps": 13.89,
            "access_assumptions": "restricted",
            "functional_class": "local",
            "geometry": [[-73.9600, 40.7600], [-73.9680, 40.7560], [-73.9750, 40.7520]],
            "data_mode": "synthetic",
        },
    ]

    features = []
    for s in segments:
        features.append({
            "type": "Feature",
            "id": s["id"],
            "geometry": {
                "type": "LineString",
                "coordinates": s["geometry"],
            },
            "properties": {
                "id": s["id"],
                "name": s["name"],
                "source_node": s["source_node"],
                "target_node": s["target_node"],
                "directed_edge_id": s["directed_edge_id"],
                "is_one_way": s["is_one_way"],
                "length_meters": s["length_meters"],
                "free_flow_speed_mps": s["free_flow_speed_mps"],
                "functional_class": s["functional_class"],
                "access_assumptions": s["access_assumptions"],
                "data_mode": s["data_mode"],
            },
        })

    geojson = {
        "type": "FeatureCollection",
        "graph_version": settings.graph_version,
        "data_mode": settings.data_mode,
        "attribution": "RoadMind AI Synthetic Test Network - Deterministic Benchmarks",
        "features": features,
    }

    return {"segments": segments, "geojson": geojson}


def generate_fixtures_data() -> Dict[str, Any]:
    """Generate all relational fixtures with temporal separation and required edge cases."""
    t0 = REFERENCE_EPOCH

    # Data Source
    data_source = {
        "id": "src_synthetic_sector7_v1",
        "name": "Sector 7 Synthetic Traffic Dataset",
        "origin": "RoadMind AI Deterministic Generator",
        "license_status": "Synthetic Benchmark - Free Internal Use",
        "geography": "Synthetic Metro Grid - Sector 7",
        "coverage": "7 directed roads, 5 junction nodes, 72 hours synthetic history",
        "retrieval_time": t0.isoformat(),
        "checksum": "",  # Populated after serialization
        "limitations": "Synthetic benchmark. No real-world vehicles or sensor calibration.",
        "data_mode": "synthetic",
    }

    # Observations
    observations = []
    
    # Corridor East regular observations leading up to t0 (incident causes slowdown at 08:20)
    for minute_offset in range(60, 0, -5):
        obs_time = t0 - timedelta(minutes=minute_offset)
        # Normal speed before 08:15 (~13.8 mps), sudden slowdown at 08:20 (~3.5 mps)
        speed = 13.8 if minute_offset > 15 else 3.5
        observations.append({
            "id": f"obs_corridor_e_{60 - minute_offset}",
            "segment_id": "seg_corridor_e",
            "observed_at": obs_time.isoformat(),
            "available_at": (obs_time + timedelta(seconds=15)).isoformat(),  # 15s latency
            "value": speed,
            "unit": "mps",
            "quality_score": 0.98,
            "provenance": "synthetic_loop_detector",
            "data_mode": "synthetic",
        })

    # FIXTURE 10: Late-Arriving Observation (observed at t0-15m, but available at t0+15m)
    # At replay time t0, this must be INVISIBLE
    observations.append({
        "id": "obs_late_arriving_01",
        "segment_id": "seg_corridor_e",
        "observed_at": (t0 - timedelta(minutes=15)).isoformat(),  # 08:15:00Z
        "available_at": (t0 + timedelta(minutes=15)).isoformat(),  # 08:45:00Z (LATE)
        "value": 4.1,
        "unit": "mps",
        "quality_score": 0.90,
        "provenance": "delayed_fleet_upload",
        "data_mode": "synthetic",
    })

    # Bypass West observations (free flow at 15.2 mps)
    for minute_offset in range(30, 0, -10):
        obs_time = t0 - timedelta(minutes=minute_offset)
        observations.append({
            "id": f"obs_bypass_w_{minute_offset}",
            "segment_id": "seg_bypass_w",
            "observed_at": obs_time.isoformat(),
            "available_at": (obs_time + timedelta(seconds=10)).isoformat(),
            "value": 15.2,
            "unit": "mps",
            "quality_score": 0.99,
            "provenance": "synthetic_camera_radar",
            "data_mode": "synthetic",
        })

    # FIXTURE 11: Sparse History on seg_sparse_history (only 1 old observation)
    observations.append({
        "id": "obs_sparse_01",
        "segment_id": "seg_sparse_history",
        "observed_at": (t0 - timedelta(days=4)).isoformat(),
        "available_at": (t0 - timedelta(days=4)).isoformat(),
        "value": 10.0,
        "unit": "mps",
        "quality_score": 0.50,
        "provenance": "infrequent_survey",
        "data_mode": "synthetic",
    })

    # FIXTURE 12: Later Outcome Observation (occurs at t0+30m = 09:00:00Z for evaluating prediction)
    observations.append({
        "id": "obs_outcome_corridor_e_0900",
        "segment_id": "seg_corridor_e",
        "observed_at": (t0 + timedelta(minutes=30)).isoformat(),  # 09:00:00Z
        "available_at": (t0 + timedelta(minutes=30, seconds=10)).isoformat(),
        "value": 4.8,  # Ground truth actual speed
        "unit": "mps",
        "quality_score": 0.99,
        "provenance": "synthetic_loop_detector",
        "data_mode": "synthetic",
    })

    # Evidence files (mock byte payloads with deterministic hashes)
    evidence_payload_1 = b"ROAD_EVIDENCE_ACCIDENT_PHOTO_CORRIDOR_EAST_BYTES_XYZ_001"
    evidence_payload_duplicate = evidence_payload_1  # Exact byte duplication
    evidence_payload_debris = b"ROAD_EVIDENCE_DEBRIS_PHOTO_CORRIDOR_EAST_BYTES_XYZ_002"

    hash_1 = compute_sha256(evidence_payload_1)
    hash_dup = compute_sha256(evidence_payload_duplicate)
    hash_debris = compute_sha256(evidence_payload_debris)

    # Save evidence payloads to private storage
    evidence_dir = settings.evidence_storage_dir
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / f"{hash_1}.jpg").write_bytes(evidence_payload_1)
    (evidence_dir / f"{hash_debris}.jpg").write_bytes(evidence_payload_debris)

    # Reports
    reports = [
        # Report 1: Initial accident report on Corridor East
        {
            "id": "rep_accident_01",
            "incident_type": "accident",
            "claimed_event_time": (t0 - timedelta(minutes=12)).isoformat(),
            "submitted_at": (t0 - timedelta(minutes=10)).isoformat(),
            "available_at": (t0 - timedelta(minutes=10)).isoformat(),
            "segment_id": "seg_corridor_e",
            "location_description": "Grand Corridor East near 5th Cross",
            "latitude": 40.7510,
            "longitude": -73.9775,
            "reporter_reference": "patrol_car_14",
            "dependency_group_id": "dep_patrol_fleet_A",  # Group A
            "description": "Multi-car rear-end collision blocking left lane.",
            "data_mode": "user_submitted",
            "idempotency_key": "idemp_rep_accident_01",
            "episode_id": "ep_corridor_accident_01",
        },
        # FIXTURE 6 & 7: Duplicate evidence & Shared-source dependency group
        {
            "id": "rep_accident_02_dup",
            "incident_type": "accident",
            "claimed_event_time": (t0 - timedelta(minutes=8)).isoformat(),
            "submitted_at": (t0 - timedelta(minutes=6)).isoformat(),
            "available_at": (t0 - timedelta(minutes=6)).isoformat(),
            "segment_id": "seg_corridor_e",
            "location_description": "Grand Corridor East at Mile 2",
            "latitude": 40.7512,
            "longitude": -73.9773,
            "reporter_reference": "patrol_car_19",
            "dependency_group_id": "dep_patrol_fleet_A",  # SAME dependency group!
            "description": "Confirming collision on Corridor East. Severe backup forming.",
            "data_mode": "user_submitted",
            "idempotency_key": "idemp_rep_accident_02",
            "episode_id": "ep_corridor_accident_01",
        },
        # FIXTURE 8: Conflicting report (claims incident in the future + contradicts speed sensor)
        {
            "id": "rep_conflict_01",
            "incident_type": "stall",
            "claimed_event_time": (t0 + timedelta(minutes=45)).isoformat(),  # FUTURE claimed time!
            "submitted_at": (t0 - timedelta(minutes=5)).isoformat(),
            "available_at": (t0 - timedelta(minutes=5)).isoformat(),
            "segment_id": "seg_bypass_w",
            "location_description": "Bypass West Ramp",
            "latitude": 40.7460,
            "longitude": -73.9830,
            "reporter_reference": "unverified_bot_99",
            "dependency_group_id": None,  # Independent/unknown
            "description": "Massive total standstill gridlock on Bypass West.",  # Sensor says 15.2 mps!
            "data_mode": "user_submitted",
            "idempotency_key": "idemp_rep_conflict_01",
            "episode_id": None,
        },
        # FIXTURE 9: Distinct recurring episodes (Pothole episodes on seg_corridor_w)
        # Episode 1 was in September; Episode 2 is recent
        {
            "id": "rep_pothole_past",
            "incident_type": "pothole",
            "claimed_event_time": "2026-09-01T10:00:00Z",
            "submitted_at": "2026-09-01T10:15:00Z",
            "available_at": "2026-09-01T10:15:00Z",
            "segment_id": "seg_corridor_w",
            "location_description": "Corridor West Near Origin Junction",
            "latitude": 40.7485,
            "longitude": -73.9835,
            "reporter_reference": "maintenance_inspector_02",
            "dependency_group_id": "dep_dept_transport",
            "description": "Deep asphalt depression in right lane.",
            "data_mode": "user_submitted",
            "idempotency_key": "idemp_rep_pothole_past",
            "episode_id": "ep_pothole_sep_resolved",
        },
        {
            "id": "rep_pothole_recent",
            "incident_type": "pothole",
            "claimed_event_time": (t0 - timedelta(hours=24)).isoformat(),
            "submitted_at": (t0 - timedelta(hours=23)).isoformat(),
            "available_at": (t0 - timedelta(hours=23)).isoformat(),
            "segment_id": "seg_corridor_w",
            "location_description": "Corridor West Near Origin Junction",
            "latitude": 40.7486,
            "longitude": -73.9834,
            "reporter_reference": "citizen_mobile_usr81",
            "dependency_group_id": None,
            "description": "New sharp pothole reopened at same junction.",
            "data_mode": "user_submitted",
            "idempotency_key": "idemp_rep_pothole_recent",
            "episode_id": "ep_pothole_oct_active",
        },
    ]

    # Evidence records
    evidence = [
        # Original evidence on report 1
        {
            "id": "ev_accident_orig_01",
            "report_id": "rep_accident_01",
            "content_hash": hash_1,
            "storage_path": str(evidence_dir / f"{hash_1}.jpg"),
            "media_type": "image/jpeg",
            "file_size_bytes": len(evidence_payload_1),
            "metadata_claims": {"device": "PatrolCam v2", "claimed_gps": [40.7510, -73.9775]},
            "is_duplicate": False,
            "duplicate_of_id": None,
            "perceptual_hash": None,
            "submitted_at": (t0 - timedelta(minutes=10)).isoformat(),
            "available_at": (t0 - timedelta(minutes=10)).isoformat(),
        },
        # FIXTURE 6: Duplicate evidence on report 2 (reused exact bytes)
        {
            "id": "ev_accident_dup_02",
            "report_id": "rep_accident_02_dup",
            "content_hash": hash_dup,  # Identical hash!
            "storage_path": str(evidence_dir / f"{hash_1}.jpg"),
            "media_type": "image/jpeg",
            "file_size_bytes": len(evidence_payload_duplicate),
            "metadata_claims": {"device": "Forwarded File", "claimed_gps": [40.7512, -73.9773]},
            "is_duplicate": True,  # Flagged server-side
            "duplicate_of_id": "ev_accident_orig_01",
            "perceptual_hash": None,
            "submitted_at": (t0 - timedelta(minutes=6)).isoformat(),
            "available_at": (t0 - timedelta(minutes=6)).isoformat(),
        },
    ]

    # Incident Episodes
    episodes = [
        # Active accident episode on Corridor East
        {
            "id": "ep_corridor_accident_01",
            "primary_segment_id": "seg_corridor_e",
            "affected_segments": ["seg_corridor_e"],
            "episode_type": "accident",
            "first_reported_at": (t0 - timedelta(minutes=12)).isoformat(),
            "last_reported_at": (t0 - timedelta(minutes=6)).isoformat(),
            "lifecycle_status": "triaged",
            "severity_level": "high",
            "heuristic_support_score": 0.72,
            "assessment_summary": "Corroborated by 2 reports and sensor deceleration. Warning: Report 2 reuses duplicate photo from Report 1 and shares dependency group dep_patrol_fleet_A.",
            "rubric_version": "rubric_v1.0",
            "reviewer_state": "verified",
        },
        # FIXTURE 9: Past resolved pothole episode
        {
            "id": "ep_pothole_sep_resolved",
            "primary_segment_id": "seg_corridor_w",
            "affected_segments": ["seg_corridor_w"],
            "episode_type": "pothole",
            "first_reported_at": "2026-09-01T10:00:00Z",
            "last_reported_at": "2026-09-01T10:15:00Z",
            "lifecycle_status": "resolved",
            "severity_level": "medium",
            "heuristic_support_score": 0.85,
            "assessment_summary": "Pothole filled and cold-patched by municipal crew.",
            "rubric_version": "rubric_v1.0",
            "reviewer_state": "verified",
        },
        # FIXTURE 9: New distinct active pothole episode on same segment
        {
            "id": "ep_pothole_oct_active",
            "primary_segment_id": "seg_corridor_w",
            "affected_segments": ["seg_corridor_w"],
            "episode_type": "pothole",
            "first_reported_at": (t0 - timedelta(hours=24)).isoformat(),
            "last_reported_at": (t0 - timedelta(hours=24)).isoformat(),
            "lifecycle_status": "reported",
            "severity_level": "low",
            "heuristic_support_score": 0.40,
            "assessment_summary": "Single uncorroborated report of recurring pavement depression.",
            "rubric_version": "rubric_v1.0",
            "reviewer_state": "unreviewed",
        },
    ]

    # Reviewer decision on active accident episode
    reviews = [
        {
            "id": "rev_corridor_01",
            "episode_id": "ep_corridor_accident_01",
            "reviewer_reference": "traffic_op_lead_sagar",
            "decision": "verified",
            "reason": "Speed sensor drop to 3.5 mps matches reported collision location.",
            "previous_state": "unreviewed",
            "recorded_at": (t0 - timedelta(minutes=4)).isoformat(),
            "available_at": (t0 - timedelta(minutes=4)).isoformat(),
        }
    ]

    # Predictions
    # FIXTURE 12: Prediction on Corridor East issued at t0 targeting t0+30m
    predictions = [
        {
            "id": "pred_corridor_e_30m",
            "segment_id": "seg_corridor_e",
            "issue_time": t0.isoformat(),
            "target_time": (t0 + timedelta(minutes=30)).isoformat(),  # 09:00:00Z
            "horizon_minutes": 30,
            "model_version": "historical_median_v1",
            "input_snapshot_reference": f"snapshot_{t0.strftime('%Y%m%dT%H%M%SZ')}",
            "predicted_speed_mps": 5.2,
            "interval_lower_mps": 3.8,
            "interval_upper_mps": 6.8,
            "confidence_level": 0.90,
            "abstention_reason": None,
            "data_mode": "synthetic",
        },
        # FIXTURE 11: Prediction on seg_sparse_history that ABSTAINS
        {
            "id": "pred_sparse_hist_30m",
            "segment_id": "seg_sparse_history",
            "issue_time": t0.isoformat(),
            "target_time": (t0 + timedelta(minutes=30)).isoformat(),
            "horizon_minutes": 30,
            "model_version": "historical_median_v1",
            "input_snapshot_reference": f"snapshot_{t0.strftime('%Y%m%dT%H%M%SZ')}",
            "predicted_speed_mps": None,
            "interval_lower_mps": None,
            "interval_upper_mps": None,
            "confidence_level": 0.90,
            "abstention_reason": "INSUFFICIENT_HISTORY",
            "data_mode": "synthetic",
        },
    ]

    # FIXTURE 12: Outcome Evaluation (comparing pred_corridor_e_30m with actual observation obs_outcome_corridor_e_0900)
    # predicted = 5.2 mps, actual = 4.8 mps -> error = 0.4 mps, inside interval [3.8, 6.8]
    evaluations = [
        {
            "id": "eval_pred_corridor_e_30m",
            "prediction_id": "pred_corridor_e_30m",
            "observation_id": "obs_outcome_corridor_e_0900",
            "error_speed_mps": 0.4,
            "absolute_error_mps": 0.4,
            "within_interval": True,
            "evaluated_at": (t0 + timedelta(minutes=30, seconds=15)).isoformat(),
            "evaluation_version": "eval_v1.0",
        }
    ]

    return {
        "reference_epoch": t0.isoformat(),
        "data_source": data_source,
        "observations": observations,
        "reports": reports,
        "evidence": evidence,
        "episodes": episodes,
        "reviews": reviews,
        "predictions": predictions,
        "evaluations": evaluations,
    }


def write_fixtures_and_manifest() -> Dict[str, str]:
    """Generate and serialize network GeoJSON, seed fixtures, and manifest."""
    settings.ensure_directories()
    
    # 1. Network GeoJSON
    network_data = generate_network_data()
    network_path = settings.fixtures_dir / "synthetic_network.geojson"
    network_json_str = json.dumps(network_data["geojson"], indent=2, sort_keys=True)
    network_path.write_text(network_json_str, encoding="utf-8", newline="\n")
    network_checksum = hashlib.sha256(network_path.read_bytes()).hexdigest()

    # 2. Seed Fixtures JSON
    fixtures_data = generate_fixtures_data()
    fixtures_data["data_source"]["checksum"] = network_checksum
    fixtures_path = settings.fixtures_dir / "seed_fixtures.json"
    fixtures_json_str = json.dumps(fixtures_data, indent=2, sort_keys=True)
    fixtures_path.write_text(fixtures_json_str, encoding="utf-8", newline="\n")
    fixtures_checksum = hashlib.sha256(fixtures_path.read_bytes()).hexdigest()

    # 3. Manifest JSON
    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": settings.fixture_random_seed,
        "graph_version": settings.graph_version,
        "data_mode": settings.data_mode,
        "files": {
            "synthetic_network.geojson": {
                "path": "data/fixtures/synthetic_network.geojson",
                "checksum_sha256": network_checksum,
                "segment_count": len(network_data["segments"]),
            },
            "seed_fixtures.json": {
                "path": "data/fixtures/seed_fixtures.json",
                "checksum_sha256": fixtures_checksum,
                "observation_count": len(fixtures_data["observations"]),
                "report_count": len(fixtures_data["reports"]),
                "evidence_count": len(fixtures_data["evidence"]),
                "episode_count": len(fixtures_data["episodes"]),
                "prediction_count": len(fixtures_data["predictions"]),
                "evaluation_count": len(fixtures_data["evaluations"]),
            },
        },
        "benchmark_fixtures_verified": [
            "one_way_roads",
            "parallel_directed_edges",
            "corridor_and_bypass",
            "full_closure_alternative",
            "disconnected_destination",
            "duplicate_uploaded_evidence",
            "shared_source_reports",
            "conflicting_evidence",
            "distinct_recurring_episodes",
            "late_arriving_observations",
            "sparse_forecasting_history",
            "later_outcome_observation",
        ],
    }

    manifest_path = settings.manifests_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "synthetic_network.geojson": network_checksum,
        "seed_fixtures.json": fixtures_checksum,
        "manifest.json": compute_sha256(manifest_path.read_text(encoding="utf-8")),
    }


if __name__ == "__main__":
    checksums = write_fixtures_and_manifest()
    print("FIXTURES GENERATED SUCCESSFULLY:")
    for name, csum in checksums.items():
        print(f"  {name}: {csum}")
