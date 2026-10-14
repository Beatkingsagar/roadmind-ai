# Architecture Decision Record (ADR) 001: Relational Schema & Temporal Model

## Status
Accepted

## Context
RoadMind AI requires an auditable decision-support architecture where traffic operators can replay past events, inspect evidence provenance, and evaluate scenario predictions. 

Key design requirements:
1. Replay time $T$ must strictly enforce temporal eligibility. Records with $\text{available\_at} > T$ must never leak into views, forecasts, or scenario inputs.
2. Heuristic evidence scores must not be treated as probabilities of truth.
3. Speed predictions must support explicit abstention rather than fabricating numbers for unobserved or stale roads.
4. Duplicate evidence must be identified by content hash and stripped of independent weight.
5. Parallel road edges must be distinguished by stable edge IDs.

## Decisions

### 1. Separation of `observed_at` and `available_at`
- `observed_at`: The exact UTC timestamp when the event or measurement physically occurred in the physical world.
- `available_at`: The exact UTC timestamp when the record was ingested and became eligible for consumption by operators and algorithms.
- **Rule**: At replay time $T$, any query for road state or forecast inputs must filter by `available_at <= T`.

### 2. Directed Multigraph Representation
- Roads are stored in `road_segments` with composite index `(source_node, target_node, directed_edge_id)`.
- Units are strictly standardized: lengths in meters, speeds in meters per second ($m/s$).
- Conversions to $km/h$ are derived helpers ($v_{km/h} = v_{m/s} \times 3.6$).

### 3. Server-Side Evidence Deduplication
- SHA-256 digests are computed over raw uploaded bytes.
- When an identical hash is encountered, `is_duplicate` is set to `True` and `duplicate_of_id` links to the original evidence.
- Shared sources are tagged with `dependency_group_id` to prevent group-level vote stacking.

### 4. Forecasting & Immutable Evaluations
- Predictions store `issue_time`, `target_time`, and explicit `abstention_reason`.
- Evaluations are stored in a separate table (`outcome_evaluations`) linking a prediction to an actual observation without mutating the historical prediction record.

## Consequences
- Guarantees zero data leakage during temporal replays.
- Supports deterministic unit and regression testing.
- Enables reproducible offline demonstrations without external database dependencies.
