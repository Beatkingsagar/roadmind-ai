# RoadMind AI — 3-Minute Hackathon Demonstration Script
**Track**: Traffic Intelligence | **Event**: NEXATHON 2026, SDIT Mangaluru  
**System**: Evidence-Aware Traffic Decision Support System

---

## Quick Reference & Preparation

### 1. Application Startup
```powershell
# Terminal 1: Backend API (FastAPI)
python -c "import sys; sys.path.insert(0, '.python_packages'); sys.path.insert(0, '.'); import uvicorn; uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8000)"

# Terminal 2: Premium Frontend (Vite)
cd apps\web
bun run dev --port 5173
```
- Open browser to **`http://localhost:5173`**.
- Verify backend status badge in topbar displays **"HEALTHY"**.

### 2. Demo Presets in Replay Bar
| Preset Name | Replay Timestamp (`at`) | Scenario Context |
| :--- | :--- | :--- |
| **Morning Free-Flow** | `2026-10-15T07:30:00Z` | Baseline corridor operation (50 km/h, 0 incidents). |
| **Incident Triage** | `2026-10-15T08:30:00Z` | Grand Corridor accident episode active (12.6 km/h, evidence review). |
| **Post-Incident Recovery** | `2026-10-15T09:30:00Z` | Incident marked resolved, recovery speed dynamics. |

### 3. Geographic Boundary & Data Honesty Notice
- **Geographic Scope**: Deterministic Synthetic Benchmark Network (Sector 7 Corridor, 7 junctions, 9 directed edges).
- **Data Provenance**: Clearly labeled throughout as synthetic sensor observations (`data_mode: "synthetic"`) with client-submitted evidence and strict epistemic abstention rules. Do not claim citywide Mangaluru GPS tracking or global addresses.

---

## 3-Minute Presentation Walkthrough

### ⏱️ 0:00 – 0:25 | The Problem & The RoadMind AI Differentiator
- **Speaker Action**: Display the **Dashboard Overview** in Dark Mode.
- **Script**:
  > *"Judges, modern navigation apps treat traffic reports blindly: ten spam reports on social media can create phantom traffic jams, while single-vehicle breakdowns that shut down arterial corridors get ignored until miles of traffic pile up.*
  > *Meet **RoadMind AI**: an evidence-aware decision support system. We don't just calculate shortest paths; we evaluate the credibility of incident evidence, test counterfactual 'what-if' scenarios, and abstain with epistemic honesty when data is stale or unobserved."*
- **Visual Cue**: Point to the **System Health**, **Data Boundary Notice** (Sector 7 Benchmark), and **Active Incident Metrics**.

---

### ⏱️ 0:25 – 0:55 | Interactive Map & Baseline Route Planning
- **Speaker Action**: Click **"Live Map"** in sidebar, then switch to **"Route Planner"**.
- **Script**:
  > *"Here is our road network. Let's plan a journey from Node A (West Entry) to Node B (East Exit). Under normal free-flow conditions, the Grand Corridor West and East take approximately 170 seconds at standard speeds."*
- **Speaker Action**:
  1. Origin: `node_origin` (Junction A).
  2. Destination: `node_destination` (Junction B).
  3. Click **"Run Scenario Comparison"**.
  4. Click the swap button (**⇄**) to show bidirectional awareness.
- **Visual Cue**: Show the primary corridor route highlighted in emerald green on the map canvas.

---

### ⏱️ 0:55 – 1:25 | Incident Ingestion & Server-Side Evidence Deduplication
- **Speaker Action**: Click **"Incidents & Review"** tab.
- **Script**:
  > *"Now, imagine a collision occurs on the Grand Corridor. A citizen submits a report. Anyone can upload a photo, but bad actors or automated bots often upload duplicate images to exaggerate traffic severity.*
  > *RoadMind AI computes server-side cryptographic SHA-256 hashes on incoming media. Exact duplicate uploads are linked to the original evidence and contribute zero independent support weight. Traffic operators audit these episodes with cryptographic credentials before recommendations adapt."*
- **Visual Cue**:
  - Point to **Episode `ep_corridor_accident_01`** (Severity: High, Heuristic Support: 0.72).
  - Open **"Operator Audit"** modal, demonstrating the verified review decision with audit timestamp.

---

### ⏱️ 1:25 – 2:00 | Counterfactual Scenario Analysis & Evidence-Sensitive Routing
- **Speaker Action**: Return to **"Route Planner"** / **"Scenarios"**. Select `seg_corridor_e` as incident segment.
- **Script**:
  > *"Here is RoadMind AI's signature feature: counterfactual scenario routing. Instead of assuming worst-case congestion immediately, our simulation engine evaluates three simultaneous realities:*
  > *1. **Baseline**: Free-flow reference corridor (170s).*
  > *2. **Partial Slowdown**: Traffic bottlenecked down to 15 km/h (takes ~300s).*
  > *3. **Full Closure**: Road completely blocked.*
  > *Notice our decision recommendation: **EVIDENCE_SENSITIVE**! The engine explains why: If the road is merely slowed down, continuing on the arterial is still acceptable; but if full blockage is confirmed by operator evidence, our South Bypass route saves 44 seconds. We give traffic commanders the sensitivity boundary!"*
- **Visual Cue**: Show the comparison cards with yellow `EVIDENCE_SENSITIVE` badge and side-by-side travel time bars.

---

### ⏱️ 2:00 – 2:30 | Epistemic Honesty: Forecasting & Road Memory
- **Speaker Action**: Click **"Forecasting"** tab.
- **Script**:
  > *"Most AI demos hallucinate numbers when data is missing. RoadMind AI refuses to lie.*
  > *For monitored segments like `seg_corridor_e`, our model forecasts short-horizon speeds (12.6 km/h) with confidence intervals.*
  > *However, if we select `seg_sparse_history`, look at what happens: the system explicitly **ABSTAINS** with the reason **STALE_OBSERVATIONS**. No fake speeds, no synthetic hallucination. In mission-critical public transit, knowing what you don't know is safety-critical."*
- **Visual Cue**:
  - Show the amber abstention banner on `seg_sparse_history`.
  - Briefly click **"Road Memory"** to show recurrence prioritization ranking (pothole recurrence vs random anomaly).

---

### ⏱️ 2:30 – 3:00 | Innovation Summary, Limitations & Future Roadmap
- **Speaker Action**: Switch to **Settings** or **Dashboard** in Light Mode (showing theme polish).
- **Script**:
  > *"To summarize: RoadMind AI is built with FastAPI and React 19, backed by 74 verified backend integration tests and a full TypeScript contract.*
  > *Our geographic boundary is currently the deterministic Sector 7 benchmark. In future milestones, we plan to integrate real OpenStreetMap corridors in Mangaluru (e.g., Hampankatta-Kottara Chowki) and connect city CCTV cameras.*
  > *Thank you, judges! We are ready for your questions."*

---

## Fallback Procedures (If Things Go Wrong)

### Fallback 1: External OpenStreetMap Tile Provider Is Slow or Unreachable
- **Symptom**: Background map tiles load slowly or show grey grid.
- **Fallback Behavior**: Leaflet vector layer still renders the exact road topology (lines, junctions, pins) with coordinate geometry.
- **Explanation to Judges**: *"Our system is completely vector-driven and computes paths on our local graph topology. The underlying raster map tiles are purely decorative and decoupled from routing intelligence."*

### Fallback 2: Resetting the Database to Clean State
If live manual testing during judging leaves unwanted test reports:
```bash
# In Terminal or via curl:
curl -X POST "http://127.0.0.1:8000/api/v1/admin/seed?reset=true" -H "X-Reviewer-Role: admin" -H "X-Reviewer-Token: traffic_operator_secret_2026"
```
Or click **"Reset & Re-seed Database"** in the **Settings** view of the frontend.
