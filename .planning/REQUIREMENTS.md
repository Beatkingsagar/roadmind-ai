# RoadMind AI — System Requirements Specification

## 1. Functional Requirements

### 1.1 Computer Vision & Media Ingestion
- **REQ-CV-01 (Media Upload)**: The system must allow users to upload image files (JPG, PNG, WebP) and video clips (MP4) containing road footage.
- **REQ-CV-02 (Defect Detection)**: The CV pipeline must detect road distress classes including Potholes, Cracks (alligator/transverse), and Obstacles with bounding boxes and confidence scores.
- **REQ-CV-03 (Severity Estimation)**: The pipeline must compute an automated severity score (`Low`, `Medium`, `High`, `Critical`) based on defect dimensions relative to road area and defect type.
- **REQ-CV-04 (Evidence Annotation)**: The system must render and persist annotated images showing detected bounding boxes, class labels, confidence scores, and hazard badges.
- **REQ-CV-05 (Geotag Ingestion)**: If image EXIF metadata contains GPS coordinates, the system must extract them automatically; otherwise, provide manual coordinate assignment or fallback geo-snapping.

### 1.2 Geospatial Map Dashboard
- **REQ-MAP-01 (Interactive Basemap)**: The dashboard must render an interactive, smooth-panning, and zooming map powered by OpenStreetMap/Leaflet.
- **REQ-MAP-02 (Severity-Coded Markers)**: Road defects and incidents must be represented by distinct, color-coded map markers reflecting severity (Critical = Red, High = Orange, Medium = Amber, Low = Emerald).
- **REQ-MAP-03 (Density Heatmap)**: The user must be able to toggle a real-time heatmap layer displaying geographic concentration of road damage and traffic incidents.
- **REQ-MAP-04 (Marker Clustering)**: The map must cluster dense groups of markers at lower zoom levels to preserve UI fluidity and declutter the viewport.
- **REQ-MAP-05 (Inspector Flyout/Modal)**: Clicking any marker must display detailed information: photographic evidence, defect classification, severity level, address/coordinates, timestamp, and incident status.
- **REQ-MAP-06 (Filtering & Search)**: Users must be able to filter map elements by severity, defect category, date range, and resolution status.

### 1.3 Incident Management & Response Dispatch
- **REQ-DISP-01 (Incident Record Creation)**: Each detected critical defect or traffic hazard must automatically generate a trackable incident record.
- **REQ-DISP-02 (Status Lifecycle)**: Support the incident progression workflow: `Reported` ➔ `Triaged` ➔ `Dispatched` ➔ `In-Progress` ➔ `Resolved`.
- **REQ-DISP-03 (Dispatch Assignment)**: Dispatchers must be able to assign maintenance crews or emergency contractors, setting target resolution deadlines and priority levels.
- **REQ-DISP-04 (Incident Audit Trail)**: The system must log state transitions with timestamps and dispatcher notes.

### 1.4 Inspection Reports & Analytics
- **REQ-REP-01 (Aggregate Metrics)**: Dashboard must display real-time KPI cards: Total Defects Detected, Active Incidents, Critical Potholes, Average Pavement Condition Index (PCI), and Repair Completion Rate.
- **REQ-REP-02 (Inspection PDF Export)**: The system must generate a professional, print-ready PDF inspection report containing executive summaries, defect tables, severity breakdown charts, and photo evidence.
- **REQ-REP-03 (Data CSV/GeoJSON Export)**: Support structured data export in CSV and standard GeoJSON formats for GIS interoperability.
- **REQ-REP-04 (Trend Analytics)**: Provide graphical breakdowns of defect distribution by type, severity distribution over time, and dispatch response velocity.

### 1.5 API & Data Persistence
- **REQ-API-01 (REST Endpoints)**: FastAPI backend must expose documented endpoints (`/api/incidents`, `/api/defects`, `/api/detect`, `/api/reports`, `/api/stats`).
- **REQ-API-02 (Async Inference)**: Image and video processing endpoints must execute asynchronously to prevent blocking the web worker threads.
- **REQ-API-03 (Data Schema)**: Database schema must support relational defect records, incident workflows, geo-coordinates, and associated media metadata.
- **REQ-API-04 (Health & Verification)**: System must expose `/api/health` providing service status, database connectivity, and model readiness.

### 1.6 User Interface & Experience
- **REQ-UI-01 (Command Center Aesthetic)**: High-density, professional command center UI with dark mode, modern typography (Inter/Outfit), crisp iconography (Lucide), and glassmorphic panels.
- **REQ-UI-02 (Responsive Layout)**: Responsive design adapting from desktop command center displays down to tablets used by field inspection teams.
- **REQ-UI-03 (Feedback & States)**: Explicit loading states, progress bars during video processing, toast notifications for dispatch events, and empty state guides.

---

## 2. Non-Functional Requirements
- **REQ-NFR-01 (Performance)**: Map marker queries and dashboard statistics must return in < 300ms.
- **REQ-NFR-02 (Inference Latency)**: Single-frame image inference must complete in < 1.5s on CPU.
- **REQ-NFR-03 (Reliability)**: Graceful handling of corrupted media files, network disconnects, or missing EXIF data.
- **REQ-NFR-04 (Portability)**: Cross-platform execution on Windows, macOS, and Linux with lightweight Python and Node dependencies.
