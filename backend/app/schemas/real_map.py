"""Schemas for Real-World Map Geocoding and Place Search."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class PlaceSearchResult(BaseModel):
    """A single geocoded real-world place."""

    id: str = Field(..., description="Stable identifier or OSM place ID")
    display_name: str = Field(..., description="Full descriptive name including region and country")
    name: str = Field(..., description="Short place or city name")
    category: Optional[str] = Field(None, description="OSM category or feature classification")
    type: Optional[str] = Field(None, description="OSM type (city, town, aerodrome, college, etc.)")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Validated latitude in WGS84 degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Validated longitude in WGS84 degrees")
    bounding_box: Optional[List[float]] = Field(
        None,
        description="Bounding coordinates [min_lat, max_lat, min_lon, max_lon]",
    )
    source: str = Field(..., description="Origin of result: 'verified_cache' | 'osm_nominatim'")
    importance: Optional[float] = Field(None, description="Search importance or ranking score")
    raw_address: Optional[Dict[str, Any]] = Field(None, description="Optional granular address components")

    @field_validator("lat")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude {v} is outside valid range [-90, 90]")
        return round(v, 6)

    @field_validator("lon")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude {v} is outside valid range [-180, 180]")
        return round(v, 6)


class PlaceSearchResponse(BaseModel):
    """Structured response from the place search geocoding endpoint."""

    query: str = Field(..., description="Normalized search query submitted")
    count: int = Field(..., ge=0, description="Number of matching results returned")
    results: List[PlaceSearchResult] = Field(default_factory=list, description="List of place search matches")
    source: str = Field(..., description="Primary provider source: 'verified_cache' | 'osm_nominatim' | 'empty'")
    attribution: str = Field(
        default="Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
        description="Required data attribution notice",
    )
