"""Static Scenario Routing Engine for RoadMind AI using NetworkX MultiDiGraph.

Implements:
- Directed multigraph preserving parallel edge identities.
- Dijkstra's shortest path based on travel time:
    travel_time_seconds = length_meters / speed_meters_per_second + delay_seconds
- Isolated scenario evaluations (baseline, slowdown, closure).
- Immutable baseline graph guarantees (baseline is never mutated).
- Reachability and boundary handling (one-way, parallel edges, origin=dest, unreachable).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx
from backend.app.models import RoadSegment
from backend.app.schemas.simulation import RouteAlternative, ScenarioOverride


class NetworkGraphManager:
    """Manages baseline and scenario MultiDiGraphs with strict immutability."""

    def __init__(self, segments: List[RoadSegment]):
        self._segments = segments
        self._baseline_graph = self._build_graph(segments)

    def _build_graph(self, segments: List[RoadSegment]) -> nx.MultiDiGraph:
        """Construct a NetworkX directed multigraph preserving edge identities."""
        G = nx.MultiDiGraph()
        for seg in segments:
            # Ensure valid traversal speed and positive length
            if seg.length_meters <= 0:
                raise ValueError(f"Segment {seg.id} length must be > 0 (got {seg.length_meters})")
            if seg.free_flow_speed_mps <= 0:
                raise ValueError(f"Segment {seg.id} free flow speed must be > 0 (got {seg.free_flow_speed_mps})")

            # Forward directed edge
            G.add_edge(
                seg.source_node,
                seg.target_node,
                key=seg.directed_edge_id,
                segment_id=seg.id,
                name=seg.name,
                length_meters=seg.length_meters,
                free_flow_speed_mps=seg.free_flow_speed_mps,
                effective_speed_mps=seg.free_flow_speed_mps,
                delay_seconds=0.0,
                is_closed=False,
                is_one_way=seg.is_one_way,
            )

            # Two-way road: add reverse edge if not one-way
            if not seg.is_one_way:
                # Use reverse key to avoid colliding with forward parallel edges
                rev_key = f"rev_{seg.directed_edge_id}"
                G.add_edge(
                    seg.target_node,
                    seg.source_node,
                    key=rev_key,
                    segment_id=seg.id,
                    name=f"{seg.name} (Reverse)",
                    length_meters=seg.length_meters,
                    free_flow_speed_mps=seg.free_flow_speed_mps,
                    effective_speed_mps=seg.free_flow_speed_mps,
                    delay_seconds=0.0,
                    is_closed=False,
                    is_one_way=False,
                )
        return G

    @property
    def baseline_graph(self) -> nx.MultiDiGraph:
        """Return a copy of the baseline graph to protect it against mutation."""
        return self._baseline_graph.copy()

    def create_scenario_graph(
        self,
        overrides: Dict[str, ScenarioOverride] | Dict[str, Dict[str, Any]] | None = None,
    ) -> nx.MultiDiGraph:
        """Create an isolated scenario graph with specified segment overrides.
        
        The baseline graph remains completely untouched.
        """
        scenario_G = self.baseline_graph
        if not overrides:
            return scenario_G

        # Normalize overrides dictionary
        norm_overrides: Dict[str, ScenarioOverride] = {}
        for seg_id, val in overrides.items():
            if isinstance(val, ScenarioOverride):
                norm_overrides[seg_id] = val
            elif isinstance(val, dict):
                norm_overrides[seg_id] = ScenarioOverride(**val)

        # Apply overrides to edges in scenario graph
        edges_to_remove = []
        for u, v, key, data in scenario_G.edges(keys=True, data=True):
            seg_id = data.get("segment_id")
            if seg_id in norm_overrides:
                override = norm_overrides[seg_id]
                if override.closed:
                    edges_to_remove.append((u, v, key))
                else:
                    if override.speed_mps is not None:
                        if override.speed_mps <= 0:
                            raise ValueError(f"Override speed for {seg_id} must be > 0 (got {override.speed_mps})")
                        data["effective_speed_mps"] = override.speed_mps
                    if override.delay_seconds < 0:
                        raise ValueError(f"Override delay for {seg_id} must be >= 0 (got {override.delay_seconds})")
                    data["delay_seconds"] = override.delay_seconds

        for u, v, key in edges_to_remove:
            scenario_G.remove_edge(u, v, key=key)

        return scenario_G


def calculate_edge_travel_time(data: Dict[str, Any]) -> float:
    """Compute travel time in seconds: length / speed + delay."""
    speed = data.get("effective_speed_mps") or data.get("free_flow_speed_mps")
    if not speed or speed <= 0:
        raise ValueError("Speed must be positive")
    delay = data.get("delay_seconds", 0.0)
    if delay < 0:
        raise ValueError("Delay must be nonnegative")
    return (data["length_meters"] / speed) + delay


def compute_fixed_route_travel_time(
    graph: nx.MultiDiGraph,
    edge_ids: List[str],
) -> Tuple[float, float, bool]:
    """Compute (length_meters, travel_time_seconds, is_reachable) along a fixed sequence of edge IDs."""
    if not edge_ids:
        return 0.0, 0.0, True

    total_len = 0.0
    total_time = 0.0

    for eid in edge_ids:
        # Search for edge in graph with matching segment_id
        matching_edge_data = None
        for u, v, key, data in graph.edges(keys=True, data=True):
            if data.get("segment_id") == eid:
                matching_edge_data = data
                break

        if not matching_edge_data:
            # Edge is closed or missing
            return 0.0, float("inf"), False

        total_len += matching_edge_data["length_meters"]
        total_time += calculate_edge_travel_time(matching_edge_data)

    return round(total_len, 2), round(total_time, 2), True


def find_optimal_route(
    graph: nx.MultiDiGraph,
    origin: str,
    destination: str,
    route_name: str = "Optimal Route",
    assumptions: str = "Reference Free-Flow",
) -> RouteAlternative:
    """Find shortest travel-time path between origin and destination on a directed multigraph."""
    # Boundary: Origin equals Destination
    if origin == destination:
        return RouteAlternative(
            route_name=route_name,
            edge_ids=[],
            nodes=[origin],
            total_length_meters=0.0,
            estimated_travel_time_seconds=0.0,
            is_reachable=True,
            assumptions_applied=assumptions,
        )

    # Boundary: Nodes not in graph
    if not graph.has_node(origin) or not graph.has_node(destination):
        return RouteAlternative(
            route_name=route_name,
            edge_ids=[],
            nodes=[],
            total_length_meters=0.0,
            estimated_travel_time_seconds=float("inf"),
            is_reachable=False,
            assumptions_applied=f"{assumptions} (Origin or Destination not found in graph)",
        )

    # Custom weight function for MultiDiGraph edges
    def edge_weight(u, v, edge_dict):
        # In NetworkX MultiDiGraph, edge_dict is {key: edge_data, ...}
        if "length_meters" in edge_dict:
            return calculate_edge_travel_time(edge_dict)
        costs = [calculate_edge_travel_time(data) for data in edge_dict.values()]
        return min(costs) if costs else float("inf")

    try:
        # Use Dijkstra to find shortest path based on travel time
        node_path = nx.shortest_path(graph, source=origin, target=destination, weight=edge_weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return RouteAlternative(
            route_name=route_name,
            edge_ids=[],
            nodes=[],
            total_length_meters=0.0,
            estimated_travel_time_seconds=float("inf"),
            is_reachable=False,
            assumptions_applied=f"{assumptions} (Destination unreachable)",
        )

    # Reconstruct exact edges traversed (preserving parallel edge identities)
    traversed_edges: List[str] = []
    total_length = 0.0
    total_time = 0.0

    for i in range(len(node_path) - 1):
        u = node_path[i]
        v = node_path[i + 1]
        
        # In a MultiDiGraph, pick the specific edge between u and v with minimum cost
        candidate_edges = graph[u][v]
        best_key = min(candidate_edges, key=lambda k: calculate_edge_travel_time(candidate_edges[k]))
        best_data = candidate_edges[best_key]

        traversed_edges.append(best_data["segment_id"])
        total_length += best_data["length_meters"]
        total_time += calculate_edge_travel_time(best_data)

    return RouteAlternative(
        route_name=route_name,
        edge_ids=traversed_edges,
        nodes=node_path,
        total_length_meters=round(total_length, 2),
        estimated_travel_time_seconds=round(total_time, 2),
        is_reachable=True,
        assumptions_applied=assumptions,
    )
