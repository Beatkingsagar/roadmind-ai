# ADR 003: FastAPI Backend, Replay Endpoints, and Reviewer Authorization Boundaries

## Context & Problem Statement
In Phase 3 of RoadMind AI (NEXATHON 2026 Hackathon, Traffic Intelligence Track), the verified Phase 2 domain services (Evidence, Scenario Router, Recommendation, Forecasting, and Road Memory) must be exposed via an auditable, modular REST API.
The API must satisfy critical hackathon requirements:
1. Versioned REST endpoints under `/api/v1` and health check at `/api/health`.
2. Safe database startup: regular application startup must never wipe or drop existing database tables.
3. Strict idempotency on report submission: re-submitting with an identical idempotency key returns the existing report; reusing a key with conflicting parameters returns HTTP 409 Conflict.
4. Server-side evidence hashing: client-provided hashes are not trusted; duplicate evidence is detected and linked, preventing score inflation.
5. Reviewer authorization boundary: public users cannot approve incidents or alter incident status; an operator header/token is strictly enforced.
6. Temporal replay filtering: records with `available_at > T` or episodes first reported after `T` are hidden at replay time `T`.
7. Network immutability: simulations never mutate baseline road network geometry or parameters.

## Considered Options
1. **Monolithic Router**: Defining all route handlers in `backend/app/main.py`.
   - *Rejected*: Violates modularity, hard to maintain and test.
2. **Resource-Centric Sub-Routers under `backend/app/api/v1/`**:
   - `network.py`: network GeoJSON, road state snapshots, segment history.
   - `reports.py`: report intake, server-side SHA-256 evidence hashing, idempotency.
   - `incidents.py`: episode listing, episode details, authorized operator review trail.
   - `forecasting.py`: baseline forecasting (persistence/historical median) with abstention, chronological evaluation.
   - `simulations.py`: single scenario runs, run retrieval by ID, scenario comparison and assumption-sensitive recommendations.
   - `memory.py`: road memory inspection priority ranking.
   - `admin.py`: operator database seeding/demo reset.
   - *Accepted*: Clean, modular, easily unit and integration testable.

## Decision Outcome
Adopt Option 2 with the following technical design:

### 1. Application Foundation & Safe Initialization
- FastAPI app initialized with `lifespan` context manager calling `init_db()` (`Base.metadata.create_all()`). Tables are created only if absent; existing data is preserved across server restarts.
- Structured exception handlers return consistent JSON conforming to `ErrorResponse`.

### 2. Idempotency & Conflict Handling
- `ReportCreate` accepts an optional `idempotency_key`.
- If key exists in SQLite: compares core fields (`incident_type`, `claimed_event_time`, `segment_id`, `latitude`, `longitude`, `description`).
  - Matches: returns HTTP 200/201 with existing report.
  - Conflicts: raises HTTP 409 Conflict with descriptive error message.

### 3. Server-Side Evidence Hashing & Deduplication
- Server calculates SHA-256 hash directly from file bytes using `compute_evidence_hash`.
- Duplicate files are detected and flagged (`is_duplicate=True`, `duplicate_of_id=<id>`).
- Duplicates contribute 0 independent weight during evidence assessment (`rubric_v1.0`).

### 4. Reviewer Authorization Boundary
- Protected endpoint `POST /api/v1/incidents/{id}/reviews`.
- Dependency `verify_reviewer_auth` requires either:
  - Header `X-Reviewer-Role: traffic_operator` (or `traffic_supervisor`, `admin`).
  - Header `X-Reviewer-Token` matching `settings.operator_token` (`ROADMIND_OPERATOR_TOKEN`).
  - Header `Authorization: Bearer <operator_token>`.
- Rejects unauthenticated requests with HTTP 403 Forbidden.

### 5. Replay Consistency
- Query parameter `at` accepts an ISO-8601 string (e.g. `2026-10-15T08:30:00Z`).
- Uses `filter_eligible_observations`, `filter_eligible_reports`, and `filter_eligible_reviews` to strictly exclude data where `available_at > at`.

## Status
Accepted and verified green across 16 integration tests and 57 unit tests (73 total passing tests).
