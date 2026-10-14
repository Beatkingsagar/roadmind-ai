# RoadMind AI — Project State & Memory

## Project Metadata
- **Project Name**: RoadMind AI — Evidence-Aware Traffic Decision Support
- **Repository Path**: `C:\RoadMind AI`
- **Current Milestone**: Milestone 1 (Hackathon MVP)
- **Current Phase**: Phase 2 Completed (All 5 Domain Services Verified) -> Preparing for Phase 3
- **Status**: Stable, Verified, Preserved for Next Session
- **Last Verification**: 57/57 Unit Tests Passing (Python 3.14 on Windows)

---

## Roadmap Status Summary
| Phase | Title | Status | Tests | Delivered Capabilities |
| :--- | :--- | :---: | :---: | :--- |
| **Phase 1** | Foundation, Data Contracts & Deterministic Fixtures | ✅ Completed | 27/27 | SQLAlchemy models, Pydantic v2 schemas, SQLite migrations/database, GeoJSON network, seed script (`pipelines/ingest/seed.py`), 12 benchmark fixtures. |
| **Phase 2** | Core Domain Services & Independent Verification | ✅ Completed | 30/30 | Evidence assessment engine, NetworkX scenario router, assumption-sensitive recommendation engine, forecasting engine (persistence & median), road memory & inspection priority. |
| **Phase 3** | FastAPI Backend, API Endpoints, Persistence & Replay | ⏳ Ready for Tomorrow | 0 (Queued) | REST endpoints connecting domain services, temporal replay middleware/filter, error handlers, and integration test suite. |
| **Phase 4** | Interactive Frontend Dashboard & Scenario Simulation UI | ⏸️ Queued | — | React 18 / Vite / TypeScript map UI, scenario comparison controls, inspector panel. |
| **Phase 5** | End-to-End Verification & Documentation Polish | ⏸️ Queued | — | Integration verification, UAT, submission documentation. |

---

## Detailed Completed Work

### Phase 1: Foundation & Deterministic Fixtures
- **Models**: `RoadSegment`, `Observation`, `Report`, `Evidence`, `IncidentEpisode`, `IncidentReview`, `Prediction`, `OutcomeEvaluation`, `SimulationRun`, `Recommendation`, `DataSource`.
- **Contracts**: Full request/response Pydantic models with strict field validation, unit constraints, and enum sets.
- **Fixtures & Manifest**: `data/fixtures/synthetic_network.geojson`, `seed_fixtures.json`, and `manifest.json` with SHA-256 integrity checksums covering all 12 edge cases (one-way roads, parallel edges, corridor/bypass, disconnected nodes, duplicate evidence, shared sources, conflicting timestamps, recurring episodes, late-arriving observations, sparse history, future outcomes, and immutable evaluations).
- **Seed Pipeline**: Idempotent database loader in `pipelines/ingest/seed.py`.

### Phase 2: Core Domain Services
- **Replay Filter** (`backend.app.services.replay.filter`):
  - Strictly enforces `available_at <= replay_time`.
- **Evidence Assessment Engine** (`backend.app.services.evidence.assessment`):
  - Server-side SHA-256 evidence hashing and duplicate-to-original linking (duplicate evidence contributes 0 independent weight).
  - Shared-source dependency grouping by `dependency_group_id` / reporter reference.
  - Anomaly detection: flags future claimed event times for review without fraudulent auto-labeling.
  - Sensor speed contradiction detection: flags warnings when physical sensors show $>80\%$ free-flow speed while reports claim gridlock.
  - Transparent rubric (`rubric_v1.0`), separating heuristic support scores from reviewer verification state.
- **Static Scenario Routing Engine** (`backend.app.services.simulation.router`):
  - Directed multigraph (`nx.MultiDiGraph`) preserving distinct parallel edge IDs.
  - Dijkstra shortest path by travel time ($T = \frac{L}{v} + d_{\text{delay}}$, requiring $v > 0, d \ge 0$).
  - Scenario overrides on graph deep-copy (ensuring baseline graph immutability).
  - `compute_fixed_route_travel_time` for direct cost evaluation of the reference corridor under degraded conditions.
- **Assumption-Sensitive Recommendation Engine** (`backend.app.services.simulation.recommendation`):
  - Signature feature: evaluates reference free-flow, partial slowdown, and full closure scenarios.
  - Uses $\ge 30s$ minimum-benefit threshold.
  - Classifies outcomes into `ROBUST_ALTERNATIVE`, `EVIDENCE_SENSITIVE`, `NO_ROUTE_AVAILABLE`, and `INSUFFICIENT_DATA` with explicit audit explanations.
- **Forecasting Engine** (`backend.app.services.forecasting.engine`):
  - Persistence baseline with 60-minute freshness window (abstains with `STALE_OBSERVATIONS`).
  - Historical time-of-week median baseline (matching weekday and $\pm 30$m window; abstains with `INSUFFICIENT_HISTORY` if $< 3$ samples).
  - Chronological outcome evaluation computing MAE and RMSE separately for 15-minute and 30-minute horizons without mutating past predictions.
- **Road Memory & Inspection Priority** (`backend.app.services.memory.road_memory`):
  - Spatiotemporal clustering of reports into `EpisodeCluster`s ($300m$ radius, $4.0h$ window).
  - Duplicate reports do not inflate `observed_recurrence_count`.
  - Audits sensor coverage ($< 5$ observations flagged as poor coverage; displays limitation warning).
  - Transparent inspection priority scoring (`inspection_v1.0`) combining recurrence, severity, duration, and coverage uncertainty.

---

## Phase 3 Progress & Tomorrow's Scope
- **Phase 3 Goal**: Build the FastAPI application connecting all domain services to clean, auditable HTTP REST endpoints.
- **Status**: Ready to begin immediately upon resuming.
- **Endpoints to Implement**:
  1. `GET /api/v1/network`: GeoJSON network structure, segments, and baseline geometries.
  2. `GET /api/v1/replay/state`: Replay-filtered snapshot of observations, active reports, and episodes at `?replay_time=ISO`.
  3. `POST /api/v1/evidence/upload`: Intake report/evidence, compute server-side SHA-256, run assessment rubric.
  4. `POST /api/v1/simulation/route`: Run baseline or single scenario route search between origin and destination.
  5. `POST /api/v1/simulation/recommend`: Run assumption sensitivity analysis across baseline, slowdown, and closure scenarios.
  6. `GET /api/v1/forecasting/predict`: Generate 15m/30m persistence or historical median forecasts with abstentions.
  7. `GET /api/v1/forecasting/evaluate`: Chronological MAE/RMSE evaluation across historical horizons.
  8. `GET /api/v1/memory/inspection-priority`: Clustered recurrence summaries and ranked inspection priority list.
  9. `POST /api/v1/seed`: Trigger idempotent database reset and reload.
- **Integration Tests**: Write FastAPI `TestClient` tests in `tests/integration/test_api_endpoints.py`.

---

## Commands for Next Session

### 1. Run Complete Test Suite
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests/unit', '-p', 'no:cacheprovider', '-v']))"
```

### 2. Seed / Reset Database
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); from backend.app.database import SessionLocal; from pipelines.ingest.seed import seed_database; s = SessionLocal(); seed_database(s, reset=True); s.close(); print('Database seeded successfully.')"
```

### 3. Start Backend Server (Once Phase 3 Router is Wired)
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000, reload=True)"
```

---

## Important Architectural Decisions & Ground Rules
1. **ADR 001**: Relational Schema & Temporal Model (`docs/decisions/001-schema-and-temporal-model.md`).
2. **ADR 002**: Core Domain Services & Assumption Sensitivity (`docs/decisions/002-core-domain-services.md`).
3. **Strict Boundaries**:
   - Never represent heuristic scores as event probabilities.
   - Never leak observations where `available_at > replay_time`.
   - Never rewrite saved historical predictions.
   - Never treat missing reports as proof that a road is safe when sensor coverage is poor.
   - Do NOT start frontend work until Phase 3 HTTP endpoints and integration tests are verified green.
