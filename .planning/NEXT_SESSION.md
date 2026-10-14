# RoadMind AI — Next Session Continuation Guide

## Checkpoint Status at Close of Day
- **Current Phase**: Phase 2 Completed & Verified. Ready to begin Phase 3.
- **Test Baseline**: **57 / 57 unit tests passing** (2.42s). Zero regressions.
- **Database**: SQLite schema and deterministic fixtures verified via idempotent seeder.
- **Domain Services**: All 5 domain services (Evidence, Router, Recommendation, Forecasting, Memory) are implemented, pure, testable, and deterministic.

---

## Continuation Checklist for Tomorrow

### Step 1: Verification Upon Reopening (2 minutes)
Before writing any new code tomorrow, verify the environment and baseline tests:
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests/unit', '-p', 'no:cacheprovider', '-v']))"
```
*Expected: 57 passed in ~2.5 seconds.*

---

### Step 2: Phase 3 Implementation (FastAPI HTTP Routers & Endpoints)
Phase 3 exposes the Phase 2 domain services via REST API:

#### 1. FastAPI App Factory & Middleware (`backend/app/main.py`)
- CORS middleware for frontend connection.
- Standard error handlers mapping domain exceptions to `ErrorResponse`.
- Lifespan handler initializing SQLite database on startup if absent.

#### 2. REST Endpoints to Implement (`backend/app/api/`)
- [ ] `GET /api/v1/network/geojson`: Returns `FeatureCollection` with all road segments and metadata.
- [ ] `GET /api/v1/network/segments`: List road segments with current speeds, free-flow speeds, and congestion ratios.
- [ ] `GET /api/v1/replay/state`: Accepts `?replay_time=ISO_TIMESTAMP`; returns eligible observations, active reports, and episode states using `backend.app.services.replay.filter`.
- [ ] `POST /api/v1/evidence/upload`: Form/JSON endpoint accepting report data + binary media; calculates server-side SHA-256, checks duplicates, groups shared sources, and returns structured `EvidenceAssessmentResult`.
- [ ] `POST /api/v1/simulation/route`: Accepts `origin`, `destination`, and optional scenario overrides; returns `RouteAlternative` with exact edge sequence.
- [ ] `POST /api/v1/simulation/recommend`: Accepts `origin`, `destination`, and `incident_segment_id`; runs baseline, slowdown, and closure scenarios, returning `SimulationRunResponse` with sensitivity classification (`ROBUST_ALTERNATIVE`, `EVIDENCE_SENSITIVE`, etc.).
- [ ] `GET /api/v1/forecasting/predict`: Accepts `segment_id`, `issue_time`, `horizon_minutes` (15 or 30), and `model_type` (`persistence` or `historical_median`); returns `PredictionResponse` with prediction interval or explicit abstention reason.
- [ ] `GET /api/v1/forecasting/evaluate`: Chronological evaluation endpoint returning `EvaluationSummary` (MAE, RMSE, interval coverage) across eligible actuals.
- [ ] `GET /api/v1/memory/inspection-priority`: Returns ranked segments by inspection priority (`inspection_v1.0`) with observation coverage warnings.
- [ ] `POST /api/v1/admin/seed`: Endpoint to re-seed or reset database for deterministic operator demos.

#### 3. Integration Tests (`tests/integration/test_api_endpoints.py`)
- Test each endpoint using `fastapi.testclient.TestClient`.
- Verify replay temporal filtering over HTTP: observations with `available_at > replay_time` must NOT appear.
- Verify duplicate upload via API correctly flags `is_duplicate` and returns assessment without score inflation.
- Verify recommendation endpoint returns expected sensitivity classification.

---

### Step 3: Server Verification Command
Once Phase 3 routers are wired:
```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000, reload=True)"
```
Test health check at `http://127.0.0.1:8000/docs` (Swagger UI).

---

## Strict Constraints for Next Session
1. **Do not start Phase 4 / Frontend** until Phase 3 HTTP endpoints and integration tests are verified.
2. **Preserve deterministic fixtures** and data contracts (`data/fixtures/synthetic_network.geojson`, `seed_fixtures.json`).
3. **Never represent heuristic scores as event probabilities**.
4. **Never leak future observations during temporal replays**.
