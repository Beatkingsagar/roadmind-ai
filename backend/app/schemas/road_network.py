"""Road network schemas and GeoJSON vector definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import DataMode


class RoadSegmentBase(BaseModel):
    id: str
    name: str
    graph_version: str = "v1.0.0"
    source_node: str
    target_node: str
    directed_edge_id: str = "edge_0"
    is_one_way: bool = False
    length_meters: float = Field(gt=0, description="Length in meters")
    free_flow_speed_mps: float = Field(gt=0, description="Free flow speed in meters per second")
    access_assumptions: str = "all_vehicles"
    functional_class: str = "arterial"
    data_mode: DataMode = DataMode.SYNTHETIC


class RoadSegmentResponse(RoadSegmentBase):
    free_flow_speed_kmph: float
    free_flow_travel_time_seconds: float
    coordinates: List[List[float]]

    model_config = ConfigDict(from_attributes=True)


class GeoJSONGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: str
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]


class NetworkGeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    graph_version: str
    data_mode: DataMode = DataMode.SYNTHETIC
    attribution: str
    features: List[GeoJSONFeature]


class RoadStateSnapshot(BaseModel):
    segment_id: str
    name: str
    source_node: str
    target_node: str
    current_speed_mps: float
    current_speed_kmph: float
    free_flow_speed_mps: float
    congestion_ratio: float  # current / free_flow
    active_incidents_count: int
    latest_observation_time: Optional[str] = None
    observation_freshness_seconds: Optional[float] = None
    provenance: str
    data_mode: DataMode
