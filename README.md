# RoadMind AI — Evidence-Aware Traffic Decision Support System

**NEXATHON 2026 Hackathon Project**  
**Track**: Traffic Intelligence  
**Institution**: SDIT, Mangaluru  
**Version**: 1.0.0 (Phase 5 Completed — Fully Integrated MVP)

---

## 1. Project Overview

RoadMind AI is an explainable traffic decision support system built for municipal operators and road authorities. Rather than treating uncorroborated crowdsourced reports as ground truth or inventing citywide traffic flow probabilities, RoadMind AI implements:

1. **Evidence Assessment Engine**: Computes server-side SHA-256 hashes, detects duplicate uploads, groups shared-source claims, detects physical sensor speed contradictions, and separates heuristic support scores from human review.
2. **Assumption-Sensitive Recommendation Engine**: Evaluates routing decisions across three explicit scenarios (Free-Flow Baseline, Partial Slowdown, and Full Closure) using NetworkX MultiDiGraph, classifying alternative routes as `ROBUST_ALTERNATIVE` vs `EVIDENCE_SENSITIVE`.
3. **Temporal Replay Filtering**: Strictly enforces `available_at <= replay_time`, preventing future traffic observations or late reports from leaking into past predictions or evaluations.
4. **Deterministic Speed Forecasting**: Provides persistence and historical time-of-week median baselines with prediction intervals and explicit abstention reasons (`INSUFFICIENT_HISTORY`, `STALE_OBSERVATIONS`).
5. **Road Memory & Inspection Priorities**: Spatiotemporally clusters incidents into distinct episodes and produces a transparent 0–100 inspection priority score that flags poor sensor coverage.
6. **Premium Web Application**: Interactive React 19 / TypeScript / Vite UI with vector Leaflet map, scenario route comparison, incident reporting with media uploads, operator review modal, Recharts forecasting with abstention notice, and dark/light themes.

---

## 2. Architecture & Tech Stack

- **Backend**: Python 3.14+, FastAPI 0.143, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite 8, Leaflet, Recharts, Lucide Icons
- **Persistence**: SQLite with foreign key enforcement via SQLAlchemy 2.0
- **Routing & Topologies**: NetworkX `MultiDiGraph` (preserving parallel directed edges)
- **Data Integrity**: SHA-256 manifest verification across deterministic benchmark fixtures

---

## 3. Installation & Environment Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.14 on Windows)
- Local `.python_packages` directory or virtual environment

### Environment Variables
Copy `.env.example` to `.env` or set the following variables:

```bash
# Server Environment
ROADMIND_ENV=development

# Database URL
DATABASE_URL=sqlite:///./backend/roadmind.db

# Storage Directories
EVIDENCE_STORAGE_PATH=./backend/storage/evidence

# Deterministic Seed Configuration
FIXTURE_RANDOM_SEED=42
GRAPH_VERSION=v1.0.0
DATA_MODE=synthetic

# Operator Authorization Secret (used for reviewing incidents and admin demo reset)
ROADMIND_OPERATOR_TOKEN=traffic_operator_secret_2026
```

---

## 4. Database Initialization & Seeding

### Safe Database Startup
Normal application startup (`backend.app.main:app`) creates tables if they are missing (`init_db()`) and **never drops or destroys existing records**.

### Seeding from Verified Fixtures
To idempotently populate or reset the database with the 12 deterministic benchmark fixtures:

```bash
# Idempotent seed (does not wipe user records):
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); from backend.app.database import SessionLocal; from pipelines.ingest.seed import seed_database; s = SessionLocal(); seed_database(s, reset=False); s.close(); print('Database seeded successfully.')"

# Full clean reset (development/demo only):
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); from backend.app.database import SessionLocal; from pipelines.ingest.seed import seed_database; s = SessionLocal(); seed_database(s, reset=True); s.close(); print('Database reset and seeded.')"
```

---

## 5. Running the Backend Server

Start the Uvicorn ASGI server:

```bash
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000, reload=True)"
```

- Interactive Swagger Documentation: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`
- Health Endpoint: `http://127.0.0.1:8000/api/health`

---

## 6. Running Unit & Integration Tests

The test suite runs with zero external service dependencies and leaves the development database untouched.

```bash
# Run full test suite (73 tests):
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests', '-p', 'no:cacheprovider', '-v']))"

# Run unit tests only (57 tests):
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests/unit', '-p', 'no:cacheprovider', '-v']))"

# Run integration tests only (16 tests):
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import pytest; sys.exit(pytest.main(['tests/integration', '-p', 'no:cacheprovider', '-v']))"
```

---

## 7. Available REST Endpoints & Examples

All core API endpoints are versioned under `/api/v1` (with `/api/health` at root).

### A. Health & System
- `GET /api/health`: System connectivity and database status.
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "app_name": "RoadMind AI",
    "database": "connected",
    "environment": "development"
  }
  ```

### B. Network & Road State
- `GET /api/v1/network`: Returns complete GeoJSON `FeatureCollection` of road network segments.
- `GET /api/v1/network/segments`: List road segments with lengths and free-flow speeds.
- `GET /api/v1/road-state?at=2026-10-15T08:30:00Z`: Temporal replay snapshot of current speeds, congestion ratios, and active incident counts across all segments.
- `GET /api/v1/segments/{id}/history?at=2026-10-15T08:30:00Z`: Segment history, recent observations, and clustered memory summary.

### C. Reports & Evidence
- `POST /api/v1/reports`: Intake incident report with idempotency protection.
  ```json
  {
    "incident_type": "accident",
    "claimed_event_time": "2026-10-15T09:00:00Z",
    "segment_id": "seg_corridor_w",
    "location_description": "Mile Marker 4",
    "latitude": 40.7485,
    "longitude": -73.9840,
    "reporter_reference": "citizen_42",
    "description": "Multi-vehicle rear-end collision.",
    "idempotency_key": "optional_unique_client_key_123"
  }
  ```
  *Submitting identical key and payload returns existing report. Submitting identical key with different payload returns `HTTP 409 Conflict`.*
- `POST /api/v1/reports/{id}/evidence`: Multipart media upload (`file`, optional `metadata_claims`). Computes SHA-256 hash server-side. Detects exact duplicates and links them to original evidence without inflating independent corroboration.

### D. Incidents & Operator Reviews
- `GET /api/v1/incidents?at=2026-10-15T08:30:00Z`: List active/historical incident episodes visible at replay time.
- `GET /api/v1/incidents/{id}?at=2026-10-15T08:30:00Z`: Incident episode detail with temporally filtered reports and review audit trail.
- `POST /api/v1/incidents/{id}/reviews`: Submit operator verification decision.
  - **Authorization Required**: Header `X-Reviewer-Role: traffic_operator` or `X-Reviewer-Token: traffic_operator_secret_2026`.
  - Body:
    ```json
    {
      "reviewer_reference": "operator_jane",
      "decision": "verified",
      "reason": "Confirmed via corridor camera #3."
    }
    ```

### E. Forecasting & Chronological Evaluation
- `GET /api/v1/forecasts?segment_id=seg_corridor_e&at=2026-10-15T08:30:00Z&horizon_minutes=15&model_type=persistence`: Returns predicted speed with nonparametric prediction interval. Abstains on stale or sparse data (`INSUFFICIENT_HISTORY`, `STALE_OBSERVATIONS`).
- `GET /api/v1/evaluations?at=2026-10-15T08:30:00Z`: Chronologically scores predictions against eligible actual observations, computing MAE and RMSE separately for 15-minute and 30-minute horizons without mutating historical records.

### F. Scenario Simulation & Assumption Sensitivity
- `POST /api/v1/simulations`: Execute an isolated custom scenario route search with overrides.
- `GET /api/v1/simulations/{id}`: Retrieve a persisted simulation run from the database.
- `POST /api/v1/simulations/compare`: Compare Baseline, Slowdown, and Closure scenarios to classify alternative routes (`ROBUST_ALTERNATIVE`, `EVIDENCE_SENSITIVE`, `NO_ROUTE_AVAILABLE`, `INSUFFICIENT_DATA`).
  ```json
  {
    "origin_node": "node_origin",
    "destination_node": "node_destination",
    "incident_segment_id": "seg_corridor_e",
    "minimum_benefit_seconds": 30.0
  }
  ```

### G. Road Memory & Inspection Priority
- `GET /api/v1/memory/priority?at=2026-10-15T08:30:00Z`: Returns transparent 0–100 inspection priority rankings across segments, providing factor explanations and flagging low observation density.

### H. Administration
- `POST /api/v1/admin/seed?reset=false`: Re-seeds database from fixtures (requires operator authorization).

---

## 8. Security & Authorization Boundaries

1. **Reviewer Boundary**: Citizen submission endpoints (`/api/v1/reports`, `/api/v1/reports/{id}/evidence`) are open to public input. Incident verification (`/api/v1/incidents/{id}/reviews`) is strictly restricted to authenticated traffic operators. Unauthenticated requests receive `HTTP 403 Forbidden`.
2. **Server-Side Evidence Hashing**: Client-provided SHA-256 hashes are disregarded; media hashes are calculated on raw bytes at upload.
3. **Private File Storage**: Uploaded files are stored in `backend/storage/evidence/` outside the web root.
4. **Current Limitation**: For the hackathon demonstration, reviewer authorization uses header-based role verification (`X-Reviewer-Role` or `X-Reviewer-Token`). Production deployment should integrate OAuth2/OIDC (e.g. Keycloak or AWS Cognito) with JWT bearer tokens.

---

---

## 9. Frontend Application (apps/web)

RoadMind AI includes a responsive, accessible, high-performance web dashboard built in `apps/web/` using React 19, TypeScript, Vite, Leaflet, and Recharts.

### Frontend Features:
- **Navy & Blue Visual Identity**: Professional municipal command center styling with Premium Light and Dark mode toggles.
- **Interactive Leaflet Network Map**: Vector polyline rendering of the Sector 7 Corridor network (`GET /api/v1/network`), dynamically colored by real-time congestion ratios (`GET /api/v1/road-state`).
- **Interactive Route Planner & Scenario Simulator**: Interactive From/Destination junction selection, map node picking, and counterfactual scenario comparison (`POST /api/v1/simulations/compare`) displaying Baseline vs Partial Slowdown vs Full Closure routes with automatic `ROBUST_ALTERNATIVE` vs `EVIDENCE_SENSITIVE` classification.
- **Temporal Replay Controls**: Global simulation clock (`?at=ISO_TIMESTAMP`) with one-click presets for Corridor Peak Incident, Baseline Free-Flow, and Post-Incident Outcome Evaluation.
- **Citizen Report & Evidence Intake**: Form submitting incident reports (`POST /api/v1/reports`) and uploading photo evidence (`POST /api/v1/reports/{id}/evidence`).
- **Operator Review & Verification Console**: Authorized incident review modal sending `X-Reviewer-Role` and `X-Reviewer-Token` headers to verify, reject, or investigate episodes with an audit trail.
- **Speed Forecasting & Uncertainty**: Recharts speed curve vs persistence/median predictions with confidence intervals and explicit abstention explanations.
- **Road Memory & Inspection Priorities**: 0–100 rubric priority rankings (`GET /api/v1/memory/priority`).
- **Empirical Accuracy Evaluations**: Backtested MAE and RMSE charts for 15-minute and 30-minute horizons.

### Running the Frontend Locally:
```bash
cd apps/web
bun install
bun run dev
```
Open `http://localhost:5173` in your browser.

### Building & Testing the Frontend:
```bash
cd apps/web
bun run tsc -b       # Type check (0 errors)
bun test            # Unit tests (8 passed)
bun run vite build  # Production bundle build
```

---

## 10. Verification & Hackathon Demonstration (Phase 5)

RoadMind AI has been verified end-to-end across both backend and frontend layers:
- **Backend Tests**: 74 / 74 passed (57 unit tests + 17 integration tests).
- **Frontend Tests**: 8 / 8 passed (formatters, network constants, and presets).
- **Type Checking**: 0 TypeScript errors (`bun run tsc -b`).
- **Linter**: 0 errors (`bun run oxlint`).
- **Production Build**: Successfully built in 1.27s (`bun run vite build`).
- **Live Verification**: Automated browser testing via subagent confirmed all views, theme switching, scenario routing, incident review, forecasting abstention, and map interactivity.

### Hackathon Presentation Guide
For the 3-minute timed judge presentation script, setup commands, demo presets, and fallback procedures, see:
👉 [docs/HACKATHON_DEMO.md](file:///c:/RoadMind%20AI/docs/HACKATHON_DEMO.md)

