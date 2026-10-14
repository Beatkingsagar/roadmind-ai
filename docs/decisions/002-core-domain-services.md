# Architecture Decision Record (ADR) 002: Core Domain Services & Assumption Sensitivity

## Status
Accepted

## Context
Phase 2 implements the core domain services for RoadMind AI:
1. Evidence Assessment Engine
2. Static Scenario Routing Engine
3. Assumption-Sensitive Recommendation Engine (Signature Feature)
4. Forecasting Engine & Chronological Evaluation
5. Road Memory & Transparent Inspection Priority

The non-negotiable boundaries require that:
- Heuristic support scores are never presented as event probabilities.
- Routing preserves parallel directed edge identities and evaluates fixed corridor paths under incident conditions.
- Recommendations classify decision robustness across tested scenarios (baseline, partial slowdown, full closure) with explicit explanation phrases.
- Forecasts enforce temporal availability at issue time, provide explicit abstentions, and chronologically compute MAE and RMSE without mutating past predictions.
- Incident episodes cluster spatiotemporally so duplicate reports do not inflate road failure counts.
- Poor observation coverage is explicitly reported rather than mistaking silence for road safety.

## Decisions

### 1. Evidence Assessment Engine (`backend.app.services.evidence.assessment`)
- Computes SHA-256 digests on raw content bytes for duplicate identification.
- Exact duplicates link to originals and contribute zero independent support points.
- Shared-source reports (matching `dependency_group_id` or reporter) are grouped to prevent confirmation stacking.
- Contradiction warnings are raised only when sensor speed measurements on the same segment within ±30 minutes show free-flow traffic (>80% free-flow speed) while reports claim gridlock.
- Claimed event timestamps in the future relative to submission are flagged as temporal inconsistencies, not immediately labeled fraudulent.
- Transparent versioned scoring rubric (`rubric_v1.0`) produces structured supporting factors, contradiction flags, and dependency warnings without inventing probabilities.

### 2. Static Scenario Routing Engine (`backend.app.services.simulation.router`)
- Network modeled via NetworkX `MultiDiGraph`.
- Edge weight: $T_{\text{travel}} = \frac{L}{v} + d_{\text{delay}}$, requiring $v > 0$ and $d \ge 0$.
- Edge identities (`segment_id`) are preserved during path reconstruction, correctly choosing between parallel local vs. express edges.
- Supports scenario overrides (closed edges, reduced speeds, additive delays) on a deep copy of the graph, ensuring baseline graph immutability.
- `compute_fixed_route_travel_time` calculates the exact traversal cost along a predetermined edge sequence, allowing direct evaluation of the baseline corridor under degraded incident conditions.

### 3. Assumption-Sensitive Recommendation Engine (`backend.app.services.simulation.recommendation`)
- Evaluates origin-destination under:
  1. Baseline reference free-flow.
  2. Partial slowdown on incident segment (e.g. 70% speed drop + delay).
  3. Full closure of incident corridor.
- Compares the reference route under incident conditions against diverting alternatives using a minimum-benefit threshold ($\Delta \ge 30s$).
- Classifies sensitivity into four auditable outcomes:
  - `ROBUST_ALTERNATIVE`: Alternative is beneficial across all tested assumptions.
  - `EVIDENCE_SENSITIVE`: Preferred route changes between slowdown and closure; confirming blockage is critical before recommending diversion.
  - `NO_ROUTE_AVAILABLE`: Destination is unreachable under total closure.
  - `INSUFFICIENT_DATA`: Destination unreachable under baseline.

### 4. Forecasting Engine (`backend.app.services.forecasting.engine`)
- Baselines implemented:
  - Persistence forecast with freshness threshold (abstains on `STALE_OBSERVATIONS` > 60m).
  - Historical time-of-week median (matching weekday and ±30m time-of-day window; abstains on `INSUFFICIENT_HISTORY` < 3 samples).
- Chronological evaluation matches predictions to actuals available at or before evaluation time, computing MAE and RMSE separately for 15-minute and 30-minute horizons.
- Saved predictions are immutable.

### 5. Road Memory & Inspection Priority (`backend.app.services.memory.road_memory`)
- Spatiotemporal clustering: groups reports within $300m$ radius (or same segment) and $4.0h$ window into single `EpisodeCluster`s.
- Duplicate reports do not increment `observed_recurrence_count`.
- Observation coverage reports sensor density; if $< 5$ observations, flags `is_coverage_poor = True` and displays explicit limitation note.
- Inspection priority scoring (`inspection_v1.0`): combines recurrence points (up to 40), severity points (up to 25), duration points (up to 20), and coverage uncertainty (15 points if unmonitored).

## Consequences
- 100% deterministic domain logic with 57 automated unit tests covering edge cases, negative boundaries, and temporal consistency.
- Ready for integration with HTTP routers and user interfaces in Phase 3.
