# Domain & Architecture Research: RoadMind AI

## 1. Domain Overview & Problem Landscape
Urban centers, highway authorities, and municipal departments struggle with two deeply intertwined challenges:
1. **Pavement & Road Surface Degradation**: Potholes, alligator cracking, rutting, and road hazards cause millions in vehicle damage, traffic slowdowns, and serious accidents. Traditional manual road inspection is slow, dangerous, subjective, and costly.
2. **Traffic Incident & Anomaly Management**: Accidents, sudden congestion, stalled vehicles, and road hazards require rapid detection, severity triage, and swift emergency/maintenance response dispatch to prevent secondary collisions and gridlock.

**RoadMind AI** unites these two domains into a unified intelligent operating platform:
- Ingesting video/image feeds (dashcam, mobile, fixed traffic cameras) to detect road distress and safety hazards.
- Quantifying damage severity (Pavement Condition Index / PCI-inspired scoring).
- Visualizing geo-tagged distress and traffic congestion on an interactive geospatial heatmap dashboard.
- Automating incident alerting and dispatch workflows for municipal and emergency teams.

---

## 2. Computer Vision for Road Condition & Hazard Detection

### 2.1 Detection Targets & Taxonomy
Modern road surface computer vision categorizes defects into key classes:
- **Potholes (D00)**: Sharp depressions in road surfaces presenting acute tire/suspension hazards.
- **Cracks (D10 / Longitudinal & D20 / Transverse / Alligator)**: Progressive structural failures indicating water ingress and sub-base deterioration.
- **Surface Rutting / Weathering (D40)**: Wear grooves and surface erosion.
- **Debris & Obstacles**: Objects, debris, or fallen hazards obstructing traffic lanes.
- **Signage & Lane Occlusion**: Missing, damaged, or obscured road signs and faded lane markers.

### 2.2 Model Architecture & Pipeline
- **YOLOv8 / YOLOv11 / ONNX Runtime**: Lightweight, highly optimized object detection architecture capable of real-time frame rates (30+ FPS on edge/CPU with ONNX Runtime or GPU acceleration).
- **Bounding Box & Confidence Filtering**: Multi-class detection with non-maximum suppression (NMS) and confidence thresholds tailored to prevent false positives from shadows and tire marks.
- **Severity Estimation Heuristic**:
  - Relative bounding box area / pixel ratio relative to road perspective.
  - Severity classification: `Low` (minor surface crack/shallow defect), `Medium` (moderate pothole/crack network), `High / Critical` (deep pothole, lane-blocking damage, immediate safety hazard).

---

## 3. Traffic Flow Anomaly Detection & Incident Dispatch

### 3.1 Anomaly Detection Signals
- **Velocity Drops & Congestion Spikes**: Sudden divergence from baseline free-flow velocity on monitored road segments.
- **Stationary Vehicle & Lane Blockage Detection**: Vehicles detected in active travel lanes with zero velocity over consecutive observation windows.
- **Hazard Correlation**: Pothole clusters or road debris coincident with sudden traffic deceleration alerts.

### 3.2 Dispatch Lifecycle & Workflows
- **Trigger**: Anomaly detected via CV feed or sensor/report stream.
- **Triage**: Automated severity scoring (Priority 1: Critical Emergency, Priority 2: Urgent Road Repair, Priority 3: Routine Maintenance).
- **Dispatch**: Generating work orders / dispatch notifications containing exact GPS coordinates, bounding-box photo evidence, and hazard class.
- **Status Lifecycle**: `Reported` -> `Triaged` -> `Dispatched` -> `In-Progress` -> `Resolved` -> `Verified`.

---

## 4. Geospatial Visualization & Dashboard Architecture

### 4.1 Mapping Layer Selection
- **Leaflet.js + React-Leaflet**:
  - Open-source, lightweight, zero external token dependencies (via OpenStreetMap tiles).
  - Robust plugins: `leaflet.heat` for density heatmaps, `leaflet.markercluster` for managing thousands of distress points without DOM degradation.
  - Customizable GeoJSON vector layers for road segments, colored by condition score (Green = Good, Amber = Fair, Red = Critical).

### 4.2 Spatial Indexing & Performance
- Store coordinates as standard WGS84 `(latitude, longitude)`.
- GeoJSON feature collections for seamless interchange between FastAPI and React.
- Bounding-box viewport querying to only fetch markers within the active map bounds during pan/zoom.

---

## 5. Technology Stack Decisions

| Component | Choice | Justification |
| :--- | :--- | :--- |
| **Frontend Framework** | React 18 + Vite + TypeScript | Lightning-fast HMR, strict type safety, modular component structure |
| **Styling & UI** | Modern CSS + Tailwind/Custom Design Tokens + Lucide Icons | High-performance glassmorphism, responsive data-dense command center layout |
| **Map Engine** | Leaflet + React-Leaflet + Leaflet.heat | Zero vendor lock-in, customizable tile layers, high performance |
| **Backend API** | FastAPI (Python 3.10+) | Native async support, high throughput, automatic OpenAPI documentation |
| **Computer Vision** | OpenCV + PyTorch / Ultralytics YOLOv8 / ONNX | Industry standard for real-time defect and object inference |
| **Data Persistence** | SQLite + JSON / Spatial query utilities | Zero-config, robust local ACID storage, easily upgraded to PostgreSQL/PostGIS |
| **Reporting Engine** | ReportLab / WeasyPrint & CSV exporter | Clean, professional municipal inspection PDF & CSV export |

---

## 6. Key Technical Risks & Mitigations
1. **Computer Vision Accuracy on Edge Hardware**: Heavy neural networks can bottleneck CPU-only servers.
   - *Mitigation*: Support optimized ONNX runtime, image resizing, and frame-skipping on video streams (e.g. 2-5 FPS inference cadence which is optimal for road inspection).
2. **Large GeoJSON Rendering Bottlenecks**: Rendering thousands of raw DOM markers causes map stutter.
   - *Mitigation*: Employ marker clustering and density heatmaps for zoomed-out views; render individual damage cards only at high zoom levels.
3. **Data Freshness & Real-Time Sync**: Dispatchers need live incident status transitions.
   - *Mitigation*: Use WebSocket or Server-Sent Events (SSE) alongside REST for instant event propagation.
