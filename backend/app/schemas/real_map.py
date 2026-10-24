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


# ---------------------------------------------------------------------------
# Real-World Road Routing Schemas (Phase 3)
# ---------------------------------------------------------------------------


class RealRouteWaypoint(BaseModel):
    """Origin or destination waypoint snapped to the road network."""

    name: str = Field(..., description="Waypoint name or description")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Snapped WGS84 latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Snapped WGS84 longitude")
    distance_to_snapped_meters: Optional[float] = Field(
        None,
        ge=0.0,
        description="Distance from input point to nearest snapped road edge in meters",
    )


class RealRouteLeg(BaseModel):
    """A single leg of a road route between two waypoints."""

    summary: str = Field(default="", description="High-level road corridor summary (e.g., 'NH 66')")
    distance_meters: float = Field(..., ge=0.0, description="Leg distance in meters")
    duration_seconds: float = Field(..., ge=0.0, description="Leg travel time in seconds")


# ---------------------------------------------------------------------------
# Live Traffic Intelligence Schemas (Phase 4)
# ---------------------------------------------------------------------------


class RealTrafficSegment(BaseModel):
    """Granular route sub-segment with provider-reported traffic conditions."""

    segment_index: int = Field(..., ge=0, description="0-indexed segment sequence")
    start_coord: List[float] = Field(..., description="WGS84 [lon, lat] segment start point")
    end_coord: List[float] = Field(..., description="WGS84 [lon, lat] segment end point")
    delay_seconds: float = Field(default=0.0, ge=0.0, description="Traffic delay on this segment in seconds")
    severity: str = Field(
        default="unknown",
        description="Congestion severity: unknown | minor | moderate | major | severe | closed",
    )
    current_speed_kmph: Optional[float] = Field(None, ge=0.0, description="Observed current speed in km/h if available")
    free_flow_speed_kmph: Optional[float] = Field(None, ge=0.0, description="Free-flow reference speed in km/h if available")
    description: Optional[str] = Field(None, description="Provider traffic section description or road label")


class RealTrafficInfo(BaseModel):
    """Structured live traffic intelligence from an external traffic provider."""

    status: str = Field(
        default="unavailable",
        description="Traffic status: 'available' | 'unavailable' | 'disabled' | 'unauthorized' | 'rate_limited' | 'error'",
    )
    provider: str = Field(default="none", description="Traffic provider identifier ('tomtom' | 'here' | 'none')")
    source_description: str = Field(
        default="No live provider configured",
        description="Human-readable provider source identification",
    )
    duration_with_traffic_seconds: Optional[float] = Field(
        None, ge=0.0, description="Total travel duration accounting for live traffic delays in seconds"
    )
    duration_with_traffic_minutes: Optional[float] = Field(
        None, ge=0.0, description="Total travel duration accounting for live traffic delays in minutes"
    )
    delay_seconds: float = Field(
        default=0.0, ge=0.0, description="Total live traffic delay relative to free-flow standard routing in seconds"
    )
    delay_minutes: float = Field(
        default=0.0, ge=0.0, description="Total live traffic delay relative to free-flow standard routing in minutes"
    )
    traffic_model: str = Field(
        default="standard_routability",
        description="Distinguishes 'live_traffic_observation', 'provider_traffic_estimate', 'standard_routability', or 'synthetic_simulation'",
    )
    fetched_at: Optional[str] = Field(
        None, description="ISO-8601 UTC timestamp when provider traffic observations were sampled"
    )
    is_stale: bool = Field(
        default=False, description="True if provider traffic observation exceeds freshness threshold"
    )
    message: str = Field(
        default="Live traffic unavailable",
        description="Clear status explanation (e.g., 'Live traffic unavailable' or 'Live traffic active: +6m delay via TomTom')",
    )
    segments: List[RealTrafficSegment] = Field(
        default_factory=list,
        description="Granular route segments with provider traffic (empty if provider has no granular segment data)",
    )


class TrafficProviderStatus(BaseModel):
    """Audit status of an individual external traffic provider."""

    provider_name: str = Field(..., description="Provider identifier ('tomtom', 'here', 'google', 'mapbox', 'osrm')")
    is_configured: bool = Field(..., description="True if credentials/URL for this provider are configured in env")
    is_available: bool = Field(..., description="True if provider is operational and usable")
    api_key_configured: bool = Field(..., description="True if private API key is configured without leaking value")
    coverage: str = Field(..., description="Geographic coverage summary in Karnataka")
    rate_limit_info: str = Field(..., description="Provider rate limit specification")
    pricing_info: str = Field(..., description="Provider pricing and quota tier summary")


class TrafficStatusResponse(BaseModel):
    """System-level traffic provider intelligence and configuration audit."""

    active_provider: str = Field(..., description="Active traffic provider ('tomtom' | 'here' | 'none')")
    is_live_traffic_enabled: bool = Field(..., description="True if live traffic calculation is active")
    cache_entries_count: int = Field(default=0, ge=0, description="Number of cached traffic records")
    cache_ttl_seconds: int = Field(default=180, ge=0, description="Cache freshness time-to-live in seconds")
    providers: List[TrafficProviderStatus] = Field(
        default_factory=list, description="Status breakdown of all evaluated traffic providers"
    )


class RealRoadRoute(BaseModel):
    """A calculated real-world driving route along actual roads."""

    route_index: int = Field(default=0, ge=0, description="0-indexed rank of this route alternative")
    is_primary: bool = Field(default=True, description="True if this is the recommended primary route")
    summary: str = Field(..., description="Corridor summary (e.g., 'NH 66')")
    distance_meters: float = Field(..., ge=0.0, description="Total route road distance in meters")
    distance_km: float = Field(..., ge=0.0, description="Distance in kilometers rounded to 2 decimal places")
    duration_seconds: float = Field(..., ge=0.0, description="Estimated standard road duration in seconds")
    duration_minutes: float = Field(..., ge=0.0, description="Estimated standard road duration in minutes rounded to 1 decimal place")
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON LineString geometry with coordinates [[lon, lat], ...]",
    )
    legs: List[RealRouteLeg] = Field(default_factory=list, description="Sub-legs of the route")
    weight_name: str = Field(default="routability", description="Weighting profile name used by provider")
    traffic: Optional[RealTrafficInfo] = Field(
        None,
        description="Live traffic intelligence for this route (None or unavailable if credentials missing or provider down)",
    )


class RealRouteRequest(BaseModel):
    """Request payload to calculate real-world road routing between two geographic points."""

    origin_lat: float = Field(..., ge=-90.0, le=90.0, description="Origin latitude in WGS84")
    origin_lon: float = Field(..., ge=-180.0, le=180.0, description="Origin longitude in WGS84")
    destination_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination latitude in WGS84")
    destination_lon: float = Field(..., ge=-180.0, le=180.0, description="Destination longitude in WGS84")
    origin_name: Optional[str] = Field(None, description="Optional human-readable label for origin place")
    destination_name: Optional[str] = Field(None, description="Optional human-readable label for destination place")
    alternatives: bool = Field(default=True, description="Request alternative routes if provider supports them")
    include_traffic: bool = Field(
        default=True, description="Attempt to fetch live traffic intelligence if external provider is configured"
    )

    @field_validator("origin_lat", "destination_lat")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude {v} is outside valid range [-90, 90]")
        return round(v, 6)

    @field_validator("origin_lon", "destination_lon")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude {v} is outside valid range [-180, 180]")
        return round(v, 6)


class RealRouteResponse(BaseModel):
    """Structured response containing verified road route geometries, standard metrics, and live traffic."""

    origin: RealRouteWaypoint = Field(..., description="Origin waypoint snapped to road network")
    destination: RealRouteWaypoint = Field(..., description="Destination waypoint snapped to road network")
    primary_route: RealRoadRoute = Field(..., description="Primary recommended road route")
    alternative_routes: List[RealRoadRoute] = Field(
        default_factory=list,
        description="Alternative routes returned by routing provider (never fabricated)",
    )
    provider: str = Field(default="osrm", description="Underlying routing engine provider")
    profile: str = Field(default="driving", description="Vehicle routing profile")
    traffic_model: str = Field(
        default="standard_routability",
        description="Traffic model identifier (distinguishes standard road estimates from live traffic or simulations)",
    )
    attribution: str = Field(
        default="Route data © OpenStreetMap contributors, OSRM Project (ODbL 1.0)",
        description="Provider usage attribution notice",
    )
    traffic: Optional[RealTrafficInfo] = Field(
        None,
        description="Live traffic intelligence for the route (indicates 'Live traffic unavailable' if provider credentials absent)",
    )
    traffic_status: str = Field(
        default="unavailable",
        description="High-level traffic status indicator: 'available' | 'unavailable' | 'disabled' | 'error'",
    )
