# RoadMind AI — Project Context & Architecture Specification

## 1. Executive Summary
**RoadMind AI** is an intelligent, full-stack smart traffic and road infrastructure management platform. It combines real-time computer vision analysis with geospatial intelligence to detect road surface distress (potholes, severe cracking, structural hazards), monitor traffic flow anomalies, and streamline emergency/maintenance response dispatch for municipal authorities, highway engineers, and traffic management centers.

---

## 2. Core Problem & Mission
Municipalities and transport authorities face mounting liabilities and escalating costs due to:
- **Delayed Road Hazard Detection**: Potholes and asphalt failures are often identified only after citizen complaints or vehicle damage claims.
- **Disconnected Incident Dispatch**: Emergency road maintenance dispatch lacks live visual evidence, GPS precision, and severity categorization.
- **Fragmented Traffic Awareness**: Traffic congestion spikes and hazardous road defects exist in silos, preventing proactive traffic rerouting and rapid hazard containment.

**Mission**: Deliver an end-to-end, real-time command center that ingests imagery/video feeds, pinpoints and classifies hazards with computer vision, displays actionable geospatial heatmaps, and orchestrates incident triage and repair workflows.

---

## 3. Key Target Users & Personas
1. **Traffic & Emergency Dispatchers**: Monitor live incident feeds, assess anomaly alerts, and dispatch emergency response units.
2. **Municipal Road Engineers & Inspectors**: Review detected road distress (potholes, cracks, rutting), examine severity analytics, and generate official inspection/repair work orders.
3. **Operations & City Planners**: Analyze aggregate road condition health indices (PCI) and historical congestion patterns to optimize infrastructure budgeting.

---

## 4. System Architecture & Tech Stack

### 4.1 Frontend Architecture
- **Framework**: React 18 + Vite + TypeScript
- **Design System**: Modern, dark-mode-first command center design with high data density, glassmorphism, responsive navigation, and smooth micro-interactions.
- **Geospatial Engine**: Leaflet + React-Leaflet + Leaflet Heatmap Layer + Marker Clustering.
- **State & Data Fetching**: React Hooks, TanStack Query / Axios, WebSockets for live telemetry.
- **UI & Icons**: Lucide React, Custom CSS design tokens, Chart.js / Recharts for traffic & distress metrics.

### 4.2 Backend Architecture
- **Framework**: Python 3.10+ with FastAPI and Uvicorn.
- **Inference Pipeline**: Computer Vision engine utilizing YOLOv8 / ONNX / OpenCV for real-time bounding box detection, classification, and severity scoring.
- **Data Persistence**: SQLite database with GeoJSON-compatible schemas, spatial queries, and incident audit trails.
- **Reporting Engine**: Automated PDF & CSV report generation for municipal inspection compliance.
- **API Interfaces**: RESTful CRUD endpoints + WebSocket/SSE for real-time hazard alerts and dispatch telemetry.

---

## 5. Milestone 1 (MVP) Scope & Deliverables
The initial release focuses on three tightly integrated functional pillars:

### Pillar 1: Computer Vision Road Condition & Incident Inference Engine
- Uploading images and video streams (dashcam/road footage).
- Automated detection of:
  - Potholes (depth/area estimation)
  - Severe cracks (alligator / transverse)
  - Road obstructions / hazards
- Severity classification (`Low`, `Medium`, `High`, `Critical`).
- Annotated image output with bounding boxes, confidence scores, and defect tags.

### Pillar 2: Interactive Geospatial Map Dashboard
- Centralized interactive map with OpenStreetMap tiles.
- Geo-tagged hazard markers with severity-coded color schemes (Red = Critical, Orange = High, Yellow = Medium, Green = Minor).
- Heatmap overlay mode showing distress density and accident-prone hotspots.
- Interactive inspector sidebar: clicking a map marker reveals photographic evidence, timestamp, GPS coordinates, and inspection history.

### Pillar 3: Incident Dispatch & Inspection Reports
- Incident triage pipeline: `Detected` -> `Triaged` -> `Dispatched` -> `In-Progress` -> `Resolved`.
- Automated priority scoring based on defect severity, road classification, and traffic impact.
- One-click Inspection & Work-Order Report generator (exportable as structured PDF and CSV data).
- Comprehensive dashboard analytics: Total defects, critical count, average Pavement Condition Index (PCI), and resolution throughput.

---

## 6. Success Criteria
- [x] End-to-end working pipeline: Upload image/video -> CV detects hazards -> Persists to DB -> Renders on interactive Map with Heatmap -> Generates exportable inspection report.
- [x] Sub-second API response times for geospatial queries.
- [x] Zero mock-only shortcuts: Real working backend, real database, functional AI inference models, and production-grade frontend UI.
