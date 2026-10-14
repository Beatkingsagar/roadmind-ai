"""Road network model preserving directed multigraph topology and parallel edge identities."""

from __future__ import annotations

import json
from typing import Any, List
from sqlalchemy import Boolean, Column, Float, Index, String, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(String(64), primary_key=True)  # e.g. "seg_corridor_north_01"
    graph_version = Column(String(32), default="v1.0.0", nullable=False)
    name = Column(String(128), nullable=False)
    functional_class = Column(String(32), default="arterial", nullable=False)  # arterial, highway, local, bypass
    
    # Directed topology
    source_node = Column(String(64), nullable=False, index=True)
    target_node = Column(String(64), nullable=False, index=True)
    directed_edge_id = Column(String(32), default="edge_0", nullable=False)  # Preserves multi-edge identity
    is_one_way = Column(Boolean, default=False, nullable=False)
    
    # Physics & traversal metrics (explicit units: meters, meters per second)
    length_meters = Column(Float, nullable=False)  # Must be > 0
    free_flow_speed_mps = Column(Float, nullable=False)  # Must be > 0 (e.g. 13.89 mps = 50 km/h)
    access_assumptions = Column(String(64), default="all_vehicles", nullable=False)
    
    # GeoJSON LineString coordinates stored as JSON string [[lon, lat], [lon, lat], ...]
    geometry_json = Column(Text, nullable=False)
    data_mode = Column(String(32), default="synthetic", nullable=False)

    # Relationships
    observations = relationship("Observation", back_populates="segment", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="segment")
    predictions = relationship("Prediction", back_populates="segment")

    __table_args__ = (
        Index("idx_segment_nodes", "source_node", "target_node", "directed_edge_id", unique=True),
    )

    @property
    def free_flow_speed_kmph(self) -> float:
        """Helper to convert meters/second to km/h."""
        return round(self.free_flow_speed_mps * 3.6, 2)

    @property
    def free_flow_travel_time_seconds(self) -> float:
        """Static free-flow travel time cost."""
        return self.length_meters / self.free_flow_speed_mps

    @property
    def coordinates(self) -> List[List[float]]:
        """Parse geometry JSON into list of coordinates."""
        return json.loads(self.geometry_json)

    def to_geojson_feature(self) -> dict[str, Any]:
        """Serialize segment to a valid GeoJSON Feature."""
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {
                "type": "LineString",
                "coordinates": self.coordinates,
            },
            "properties": {
                "id": self.id,
                "name": self.name,
                "source_node": self.source_node,
                "target_node": self.target_node,
                "directed_edge_id": self.directed_edge_id,
                "is_one_way": self.is_one_way,
                "length_meters": self.length_meters,
                "free_flow_speed_mps": self.free_flow_speed_mps,
                "free_flow_speed_kmph": self.free_flow_speed_kmph,
                "functional_class": self.functional_class,
                "access_assumptions": self.access_assumptions,
                "data_mode": self.data_mode,
            },
        }

    def __repr__(self) -> str:
        return f"<RoadSegment id={self.id} {self.source_node}->{self.target_node} ({self.directed_edge_id})>"
