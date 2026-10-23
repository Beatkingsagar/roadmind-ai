"""Incident report and evidence submission API endpoints."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.config import settings
from backend.app.models import Evidence, IncidentEpisode, Report, RoadSegment
from backend.app.schemas.common import DataMode
from backend.app.schemas.evidence import EvidenceResponse
from backend.app.schemas.report import ReportCreate, ReportResponse
from backend.app.services.evidence.assessment import (
    assess_evidence_for_reports,
    compute_evidence_hash,
)
from backend.app.services.replay.filter import ensure_utc

router = APIRouter(tags=["Reports & Evidence"])


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an incident report with idempotency protection and episode linking",
)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
) -> Report:
    """Submit a citizen or operator incident report.

    Features:
    - Idempotency: Re-submitting with an identical idempotency key returns the existing report.
    - Conflict Detection: Using an existing key with altered data yields HTTP 409 Conflict.
    - Spatiotemporal Clustering: Associates report with an open incident episode or initiates one.
    """
    # 1. Validate road segment exists
    segment = db.query(RoadSegment).filter(RoadSegment.id == body.segment_id).first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road segment with id '{body.segment_id}' does not exist.",
        )

    # 2. Check Idempotency Key
    if body.idempotency_key:
        existing_report = (
            db.query(Report)
            .filter(Report.idempotency_key == body.idempotency_key)
            .first()
        )
        if existing_report:
            # Check for identical payload
            same_type = (existing_report.incident_type == body.incident_type.value)
            same_segment = (existing_report.segment_id == body.segment_id)
            same_event_time = (
                abs(
                    (
                        ensure_utc(existing_report.claimed_event_time)
                        - ensure_utc(body.claimed_event_time)
                    ).total_seconds()
                )
                < 1.0
            )
            same_lat = abs(existing_report.latitude - body.latitude) < 1e-5
            same_lon = abs(existing_report.longitude - body.longitude) < 1e-5
            same_desc = existing_report.description.strip() == body.description.strip()

            if same_type and same_segment and same_event_time and same_lat and same_lon and same_desc:
                # Idempotent match: return existing record
                return existing_report

            # Key reused with differing data
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Idempotency conflict: key '{body.idempotency_key}' has already "
                    "been used with different report parameters."
                ),
            )

    now = datetime.now(timezone.utc)
    report_id = f"rep_{uuid.uuid4().hex[:8]}"

    # 3. Associate with an active episode or create a new one
    event_time = ensure_utc(body.claimed_event_time)
    active_episode = (
        db.query(IncidentEpisode)
        .filter(
            IncidentEpisode.primary_segment_id == body.segment_id,
            IncidentEpisode.episode_type == body.incident_type.value,
            IncidentEpisode.lifecycle_status != "resolved",
        )
        .order_by(IncidentEpisode.last_reported_at.desc())
        .first()
    )

    assigned_episode_id: str
    if active_episode and abs((event_time - ensure_utc(active_episode.last_reported_at)).total_seconds()) <= 4 * 3600:
        assigned_episode_id = active_episode.id
        if event_time > ensure_utc(active_episode.last_reported_at):
            active_episode.last_reported_at = event_time
    else:
        assigned_episode_id = f"ep_{uuid.uuid4().hex[:8]}"
        new_episode = IncidentEpisode(
            id=assigned_episode_id,
            primary_segment_id=body.segment_id,
            affected_segments_json=json.dumps([body.segment_id]),
            episode_type=body.incident_type.value,
            first_reported_at=event_time,
            last_reported_at=event_time,
            lifecycle_status="reported",
            severity_level="medium",
            heuristic_support_score=0.35,
            assessment_summary=f"Initial single-source submission for {body.incident_type.value}.",
            rubric_version="rubric_v1.0",
            reviewer_state="unreviewed",
        )
        db.add(new_episode)
        db.flush()

    # 4. Create and persist Report
    report = Report(
        id=report_id,
        incident_type=body.incident_type.value,
        claimed_event_time=event_time,
        submitted_at=now,
        available_at=now,
        segment_id=body.segment_id,
        location_description=body.location_description,
        latitude=body.latitude,
        longitude=body.longitude,
        reporter_reference=body.reporter_reference,
        dependency_group_id=body.dependency_group_id,
        description=body.description,
        data_mode="user_submitted",
        idempotency_key=body.idempotency_key,
        episode_id=assigned_episode_id,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@router.post(
    "/reports/{id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media evidence for an existing report with server-side hashing and duplicate detection",
)
async def upload_evidence(
    id: str,
    file: UploadFile = File(..., description="Binary media file (image/photo/video)"),
    metadata_claims: Optional[str] = Form(
        None,
        description="Optional JSON string of client-reported metadata (e.g. EXIF camera timestamps)",
    ),
    db: Session = Depends(get_db),
) -> Evidence:
    """Intake and evaluate media evidence for a report.

    Security & Deduplication Rules:
    - Evidence hashes are computed strictly on the server (SHA-256).
    - Duplicates are linked to the original evidence; duplicate uploads contribute
      zero independent support weight to prevent manipulation.
    - Files are saved to a private storage directory outside web root.
    """
    # 1. Verify parent report exists
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{id}' not found.",
        )

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "mp4"}
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
    }
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    ext = (file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "")
    if ext not in ALLOWED_EXTENSIONS or (
        file.content_type
        and file.content_type not in ALLOWED_MIME_TYPES
        and file.content_type != "application/octet-stream"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media format. Allowed formats: JPG, PNG, WebP, GIF, MP4.",
        )

    # 2. Read media content bytes
    media_bytes = await file.read()
    if not media_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )
    if len(media_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum allowed size of 10 MB.",
        )

    # 3. Server-side SHA-256 calculation
    content_hash = compute_evidence_hash(media_bytes)

    # 4. Check for duplicate evidence in database
    existing_evidence = (
        db.query(Evidence).filter(Evidence.content_hash == content_hash).first()
    )

    evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    # Parse metadata claims safely
    claims_dict = {}
    if metadata_claims:
        try:
            claims_dict = json.loads(metadata_claims)
        except Exception:
            claims_dict = {"raw_claims": metadata_claims}

    if existing_evidence:
        # Detected duplicate
        is_duplicate = True
        duplicate_of_id = existing_evidence.id
        storage_path = existing_evidence.storage_path
    else:
        # Brand new evidence file
        is_duplicate = False
        duplicate_of_id = None
        settings.ensure_directories()
        clean_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        storage_file = settings.evidence_storage_dir / f"{evidence_id}_{content_hash[:12]}.{clean_ext}"
        storage_file.write_bytes(media_bytes)
        storage_path = str(storage_file)

    evidence = Evidence(
        id=evidence_id,
        report_id=report.id,
        content_hash=content_hash,
        storage_path=storage_path,
        media_type=file.content_type or "image/jpeg",
        file_size_bytes=len(media_bytes),
        metadata_claims_json=json.dumps(claims_dict),
        is_duplicate=is_duplicate,
        duplicate_of_id=duplicate_of_id,
        submitted_at=now,
        available_at=now,
    )

    db.add(evidence)
    db.flush()

    # 5. Re-run evidence assessment for the associated episode
    if report.episode_id:
        episode = db.query(IncidentEpisode).filter(IncidentEpisode.id == report.episode_id).first()
        segment = db.query(RoadSegment).filter(RoadSegment.id == report.segment_id).first()
        if episode and segment:
            episode_reports = db.query(Report).filter(Report.episode_id == episode.id).all()
            assessment = assess_evidence_for_reports(db, episode_reports, segment, replay_time=now)
            episode.heuristic_support_score = assessment.heuristic_support_score
            episode.assessment_summary = assessment.generate_summary()

    db.commit()
    db.refresh(evidence)

    return evidence
