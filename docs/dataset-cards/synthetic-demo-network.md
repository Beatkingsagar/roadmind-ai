# Dataset Card: Sector 7 Synthetic Benchmark Network

## 1. Dataset Summary
- **Identifier**: `src_synthetic_sector7_v1`
- **Name**: Sector 7 Synthetic Traffic Dataset
- **Version**: 1.0.0
- **Generator**: `pipelines/ingest/generate_fixtures.py`
- **Random Seed**: 42 (fixed deterministic seed)
- **Data Mode**: `synthetic` (explicitly distinct from real-world telemetry)
- **License**: Synthetic Benchmark — Internal Decision-Support Hackathon Demonstration

---

## 2. Provenance & Data Honesty
This dataset is **100% synthetically generated** for auditable algorithm testing and offline demonstration. 
- It does **NOT** represent any real municipal traffic network or actual sensor deployment.
- No external proprietary or paid traffic APIs were used.
- Coordinates are situated in a bounded test bounding box in standard WGS84 GeoJSON format.
- Synthetic timestamps are pinned around reference epoch `2026-10-15T08:30:00Z`.

---

## 3. Road Network Topology & Units

| Property | Unit | Constraints & Validation |
| :--- | :--- | :--- |
| **Length** | Meters ($m$) | Strictly positive ($> 0.0$) |
| **Speed** | Meters per second ($m/s$) | Strictly positive for traversable roads ($> 0.0$); conversions to $km/h$ via $\times 3.6$ |
| **Travel Time** | Seconds ($s$) | Free flow: $T = \frac{\text{length\_meters}}{\text{free\_flow\_speed\_mps}}$ |
| **Coordinates** | Degrees WGS84 | $[ \text{longitude}, \text{latitude} ]$ GeoJSON standard |

---

## 4. Benchmark Test Fixtures Included

1. **One-Way Road (`seg_oneway_north`)**: Traversable South-to-North only; no reverse edge exists.
2. **Parallel Directed Edges (`seg_corridor_w` vs `seg_corridor_w_express`)**: Both connect `node_origin` to `node_corridor_mid` with distinct `directed_edge_id` values (`edge_0` vs `edge_express_1`).
3. **Corridor and Bypass**: Main arterial corridor and slower southern bypass route connecting Origin to Destination.
4. **Disconnected Destination (`node_isolated`)**: Isolated node with zero incoming edges to verify unreachable destination handling.
5. **Duplicate Uploaded Evidence (`ev_accident_orig_01` vs `ev_accident_dup_02`)**: Identical byte payloads with matching SHA-256 hashes; server flags duplicate and awards 0 independent support.
6. **Shared-Source Reports (`rep_accident_01` and `rep_accident_02_dup`)**: Linked via `dependency_group_id = dep_patrol_fleet_A`.
7. **Conflicting Evidence (`rep_conflict_01`)**: Future claimed event timestamp and claims severe standstill while speed sensor reads $15.2\ m/s$.
8. **Sparse History (`seg_sparse_history`)**: Segment with only 1 historic observation 4 days old; triggers explicit forecast abstention (`INSUFFICIENT_HISTORY`).
9. **Distinct Recurring Episodes (`ep_pothole_sep_resolved` vs `ep_pothole_oct_active`)**: Separated by weeks on the same segment to demonstrate recurrence tracking without misclassifying as repeated failures.
10. **Late-Arriving Observation (`obs_late_arriving_01`)**: Observed at $T_0 - 15m$, but available at $T_0 + 15m$. Invisible at replay $T_0$.
11. **Later Outcome Observation (`obs_outcome_corridor_e_0900`)**: Observed at $T_0 + 30m$ for immutable evaluation of prediction `pred_corridor_e_30m`.
