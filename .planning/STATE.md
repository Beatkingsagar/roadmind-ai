# RoadMind AI — Project State & Memory

## Project Metadata
- **Project Name**: RoadMind AI — Evidence-Aware Traffic Decision Support
- **Repository Path**: `C:\RoadMind AI`
- **Current Milestone**: Milestone 1 (Hackathon MVP)
- **Current Phase**: Phase 3 Completed (FastAPI Backend, Replay Endpoints, Persistence & Integration Testing) -> Preparing for Phase 4
- **Status**: Stable, Verified, Preserved for Next Session
- **Last Verification**: 73/73 Tests Passing (57 Unit Tests + 16 Integration Tests on Python 3.14 on Windows)

---

## Roadmap Status Summary
| Phase | Title | Status | Tests | Delivered Capabilities |
| :--- | :--- | :---: | :---: | :--- |
| **Phase 1** | Foundation, Data Contracts & Deterministic Fixtures | ✅ Completed | 27/27 | SQLAlchemy models, Pydantic v2 schemas, SQLite migrations/database, GeoJSON network, seed script (`pipelines/ingest/seed.py`), 12 benchmark fixtures. |
| **Phase 2** | Core Domain Services & Independent Verification | ✅ Completed | 30/30 | Evidence assessment engine, NetworkX scenario router, assumption-sensitive recommendation engine, forecasting engine (persistence & median), road memory & inspection priority. |
| **Phase 3** | FastAPI Backend, API Endpoints, Persistence & Replay | ✅ Completed | 16/16 | REST endpoints connecting domain services, temporal replay filtering, server-side SHA-256 evidence hashing, idempotency protection, reviewer authorization boundaries, and 16 integration tests. |
| **Phase 4** | Interactive Frontend Dashboard & Scenario Simulation UI | ⏳ Next Up | — | React / Vite / TypeScript map UI, scenario comparison controls, inspector panel. |
| **Phase 5** | End-to-End Verification & Documentation Polish | ⏸️ Queued | — | Integration verification, UAT, submission documentation. |

---

## Detailed Completed Work

### Phase 1: Foundation & Deterministic Fixtures
- **Models**: `RoadSegment`, `Observation`, `Report`, `Evidence`, `IncidentEpisode`, `IncidentReview`, `Prediction`, `OutcomeEvaluation`, `SimulationRun`, `Recommendation`, `DataSource`.
- **Contracts**: Full request/response Pydantic models with strict field validation, unit constraints, and enum sets.
- **Fixtures & Manifest**: `data/fixtures/synthetic_network.geojson`, `seed_fixtures.json`, and `manifest.json` with SHA-256 integrity checksums covering all 12 edge cases.
- **Seed Pipeline**: Idempotent database loader in `pipelines/ingest/seed.py`.

### Phase 2: Core Domain Services
- **Replay Filter** (`backend.app.services.replay.filter`):
  - Strictly enforces `available_at <= replay_time`.
- **Evidence Assessment Engine** (`backend.app.services.evidence.assessment`):
  - Server-side SHA-256 evidence hashing and duplicate-to-original linking (duplicate evidence contributes 0 independent weight).
  - Shared-source dependency grouping by `dependency_group_id` / reporter reference.
  - Transparent rubric (`rubric_v1.0`), separating heuristic support scores from reviewer verification state.
- **Static Scenario Routing Engine** (`backend.app.services.simulation.router`):
  - Directed multigraph (`nx.MultiDiGraph`) preserving distinct parallel edge IDs.
  - Dijkstra shortest path by travel time ($T = \frac{L}{v} + d_{\text{delay}}$, requiring $v > 0, d \ge 0$).
  - Scenario overrides on graph deep-copy (ensuring baseline graph immutability).
- **Assumption-Sensitive Recommendation Engine** (`backend.app.services.simulation.recommendation`):
  - Evaluates reference free-flow, partial slowdown, and full closure scenarios.
  - Classifies outcomes into `ROBUST_ALTERNATIVE`, `EVIDENCE_SENSITIVE`, `NO_ROUTE_AVAILABLE`, and `INSUFFICIENT_DATA`.
- **Forecasting Engine** (`backend.app.services.forecasting.engine`):
  - Persistence baseline with 60-minute freshness window (abstains with `STALE_OBSERVATIONS`).
  - Historical time-of-week median baseline (abstains with `INSUFFICIENT_HISTORY` if $< 3$ samples).
  - Chronological outcome evaluation computing MAE and RMSE separately for 15-minute and 30-minute horizons without mutating past predictions.
- **Road Memory & Inspection Priority** (`backend.app.services.memory.road_memory`):
  - Spatiotemporal clustering of reports into `EpisodeCluster`s ($300m$ radius, $4.0h$ window).
  - Transparent inspection priority scoring (`inspection_v1.0`) combining recurrence, severity, duration, and coverage uncertainty.

### Phase 3: FastAPI Backend & Integration Testing
- **Application Factory** (`backend/app/main.py`):
  - Lifespan context manager with safe, non-destructive `init_db()` table creation.
  - Health check endpoint at `/api/health`.
  - Structured exception handlers mapping errors to `ErrorResponse`.
  - CORS middleware supporting configurable origins.
- **API Endpoints Implemented & Verified**:
  - `GET /api/health`: Health status and database connectivity.
  - `GET /api/v1/network` & `/api/v1/network/geojson`: Full GeoJSON FeatureCollection.
  - `GET /api/v1/network/segments`: List network segments with traversal specs.
  - `GET /api/v1/road-state?at=...`: Replay-filtered dynamic speeds, congestion ratios, and active incident counts.
  - `POST /api/v1/reports`: Citizen report intake with idempotency check (identical -> returns existing; conflict -> HTTP 409) and episode auto-clustering.
  - `POST /api/v1/reports/{id}/evidence`: Multipart media upload with server-side SHA-256 hashing, duplicate detection, and score re-assessment.
  - `GET /api/v1/incidents?at=...`: Temporal list of incident episodes visible at cutoff.
  - `GET /api/v1/incidents/{id}?at=...`: Episode details with temporally filtered reports and review audit trail.
  - `POST /api/v1/incidents/{id}/reviews`: Operator review endpoint guarded by reviewer authorization boundary (`verify_reviewer_auth`).
  - `GET /api/v1/forecasts`: Persistence or median forecast with explicit abstention reason.
  - `GET /api/v1/evaluations`: Chronological MAE/RMSE scoring against revealed actual observations.
  - `POST /api/v1/simulations`: Isolated custom scenario route search.
  - `GET /api/v1/simulations/{id}`: Retrieval of persisted simulation runs from database.
  - `POST /api/v1/simulations/compare`: 3-way scenario sensitivity analysis (Baseline, Slowdown, Closure) with recommendation.
  - `GET /api/v1/segments/{id}/history?at=...`: Segment profile, recent observations, and clustered memory summary.
  - `GET /api/v1/memory/priority?at=...`: Ranked segments by inspection priority score (0–100).
  - `POST /api/v1/admin/seed`: Protected demo database seeder/safe reset.
- **Integration Tests** (`tests/integration/test_api_endpoints.py`):
  - 16/16 integration tests passing, verifying all 13 required categories including idempotency, evidence hashing, reviewer auth boundaries, temporal replay, immutability, and database persistence across application restarts.
- **Decisions & Documentation**:
  - ADR 003 (`docs/decisions/003-fastapi-backend-and-temporal-endpoints.md`).
  - Comprehensive `README.md` with installation, running, API endpoints, testing, and security boundaries.

---

## Commands for Verification

### 1. Run Complete Test Suite (73 Tests)
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests', '-p', 'no:cacheprovider', '-v']))"
```

### 2. Start Backend Server
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000, reload=True)"
```

---

## Important Architectural Decisions & Ground Rules
1. **ADR 001**: Relational Schema & Temporal Model (`docs/decisions/001-schema-and-temporal-model.md`).
2. **ADR 002**: Core Domain Services & Assumption Sensitivity (`docs/decisions/002-core-domain-services.md`).
3. **ADR 003**: FastAPI Backend, Replay Endpoints & Reviewer Boundaries (`docs/decisions/003-fastapi-backend-and-temporal-endpoints.md`).
4. **Strict Boundaries**:
   - Never represent heuristic scores as event probabilities.
   - Never leak observations where `available_at > replay_time`.
   - Never rewrite saved historical predictions.
   - Never mutate baseline network geometry or costs during scenario simulations.
   - Guard reviewer endpoints against public unauthenticated access.
   - Complete Phase 3 verification before starting Phase 4 frontend.
