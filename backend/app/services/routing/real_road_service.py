"""Real-world road routing service using external routing engine (OSRM).

Provides:
- Turn-by-turn road network routing between real geographic coordinates (WGS84).
- GeoJSON LineString route geometries for Leaflet mapping.
- Exact road distance (meters and kilometers) and estimated driving duration.
- Alternative routes only when returned by the routing provider.
- Clear distinction of standard road routability from live traffic or synthetic simulations.
- Resilient error handling for invalid coordinates, unreachable provider, timeouts, and no-route responses.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import settings
from backend.app.schemas.real_map import (
    RealRoadRoute,
    RealRouteLeg,
    RealRouteRequest,
    RealRouteResponse,
    RealRouteWaypoint,
)

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Base exception for routing failures."""


class InvalidRouteCoordinatesError(RoutingError):
    """Raised when coordinates are out of bounds or origin and destination are identical."""


class NoRouteFoundError(RoutingError):
    """Raised when the routing engine finds no drivable road path between coordinates."""


class RoutingTimeoutError(RoutingError):
    """Raised when the external routing service fails to respond in time."""


class RoutingRateLimitError(RoutingError):
    """Raised when the external routing service rate limits the application."""


class RoutingProviderError(RoutingError):
    """Raised when the external routing service returns an unexpected error or is unreachable."""


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate approximate great-circle distance between two WGS84 points in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class RealRoadRoutingService:
    """Service for querying real-world road routes via OSRM."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.osrm_routing_url).rstrip("/")
        self._route_cache: Dict[str, RealRouteResponse] = {}

    def calculate_route(
        self,
        request: RealRouteRequest,
        bypass_cache: bool = False,
    ) -> RealRouteResponse:
        """Calculate real road route between origin and destination coordinates.

        Args:
            request: RealRouteRequest with origin and destination lat/lon.
            bypass_cache: If True, bypasses internal memory cache and queries provider.

        Returns:
            RealRouteResponse with primary route, geometry, distance, and duration.
        """
        # 1. Coordinate Validation
        self._validate_coordinates(
            request.origin_lat,
            request.origin_lon,
            request.destination_lat,
            request.destination_lon,
        )

        # 2. Check Cache
        cache_key = (
            f"{request.origin_lat:.5f},{request.origin_lon:.5f}->"
            f"{request.destination_lat:.5f},{request.destination_lon:.5f}:"
            f"alt={request.alternatives}"
        )
        if not bypass_cache and cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            # Override custom names if provided in current request
            if request.origin_name or request.destination_name:
                return cached.model_copy(
                    update={
                        "origin": cached.origin.model_copy(
                            update={"name": request.origin_name or cached.origin.name}
                        ),
                        "destination": cached.destination.model_copy(
                            update={"name": request.destination_name or cached.destination.name}
                        ),
                    }
                )
            return cached

        # 3. Query External OSRM Engine
        osrm_data = self._query_osrm(
            origin_lon=request.origin_lon,
            origin_lat=request.origin_lat,
            dest_lon=request.destination_lon,
            dest_lat=request.destination_lat,
            alternatives=request.alternatives,
        )

        # 4. Parse Routes and Waypoints
        response = self._parse_osrm_response(osrm_data, request)

        # 5. Cache and Return
        self._route_cache[cache_key] = response
        return response

    def _validate_coordinates(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> None:
        """Validate WGS84 range and ensure origin and destination are distinct."""
        for name, lat, lon in [("Origin", origin_lat, origin_lon), ("Destination", dest_lat, dest_lon)]:
            if math.isnan(lat) or math.isnan(lon):
                raise InvalidRouteCoordinatesError(f"{name} coordinates contain NaN values.")
            if not (-90.0 <= lat <= 90.0):
                raise InvalidRouteCoordinatesError(f"{name} latitude {lat} outside valid range [-90, 90].")
            if not (-180.0 <= lon <= 180.0):
                raise InvalidRouteCoordinatesError(f"{name} longitude {lon} outside valid range [-180, 180].")

        dist_meters = _haversine_distance_meters(origin_lat, origin_lon, dest_lat, dest_lon)
        if dist_meters < 20.0:
            raise InvalidRouteCoordinatesError(
                "Origin and destination coordinates are too close or identical "
                f"({dist_meters:.1f}m separation). Please specify distinct locations."
            )

    def _query_osrm(
        self,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
        alternatives: bool = True,
    ) -> Dict[str, Any]:
        """Send HTTP request to OSRM route service.

        Note: OSRM expects coordinates in '{lon},{lat};{lon},{lat}' ordering.
        """
        alt_str = "true" if alternatives else "false"
        url = (
            f"{self.base_url}/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            f"?overview=full&geometries=geojson&alternatives={alt_str}&steps=true"
        )
        headers = {
            "User-Agent": "RoadMindAI-RoadRouting/1.0 (https://github.com/Beatkingsagar/roadmind-ai)",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0, headers=headers) as client:
                resp = client.get(url)
        except httpx.TimeoutException as err:
            logger.warning("OSRM routing provider timed out: %s", err)
            raise RoutingTimeoutError("Routing provider timed out after 10.0s.") from err
        except (httpx.ConnectError, httpx.NetworkError) as err:
            logger.error("OSRM routing provider network error: %s", err)
            raise RoutingProviderError(
                f"Could not connect to road routing provider at {self.base_url}."
            ) from err
        except Exception as err:
            logger.error("Unexpected error connecting to routing provider: %s", err)
            raise RoutingProviderError(f"Routing request failed: {err}") from err

        if resp.status_code == 429:
            raise RoutingRateLimitError("Routing provider rate limit exceeded. Please wait a moment.")

        if resp.status_code >= 500:
            raise RoutingProviderError(
                f"Routing provider returned server error: HTTP {resp.status_code}."
            )

        try:
            data = resp.json()
        except Exception as err:
            raise RoutingProviderError("Malformed JSON response from routing provider.") from err

        code = data.get("code")
        if code == "NoRoute":
            raise NoRouteFoundError(
                "No drivable road route was found between the selected coordinates. "
                "The locations may be on disconnected landmasses or lack road network access."
            )
        if code == "InvalidQuery":
            raise InvalidRouteCoordinatesError(
                f"Routing provider rejected query coordinates: {data.get('message', 'Invalid query')}"
            )
        if code != "Ok":
            raise RoutingProviderError(
                f"Routing provider returned status '{code}': {data.get('message', 'Unknown routing error')}"
            )

        return data

    def _parse_osrm_response(
        self,
        data: Dict[str, Any],
        request: RealRouteRequest,
    ) -> RealRouteResponse:
        """Parse OSRM GeoJSON response into typed RealRouteResponse model."""
        routes_data = data.get("routes", [])
        if not routes_data:
            raise NoRouteFoundError("No road routes returned by provider.")

        parsed_routes: List[RealRoadRoute] = []
        for idx, r in enumerate(routes_data):
            dist_meters = float(r.get("distance", 0.0))
            dur_seconds = float(r.get("duration", 0.0))
            geometry = r.get("geometry", {})
            weight_name = r.get("weight_name", "routability")

            # Parse legs
            legs: List[RealRouteLeg] = []
            for leg in r.get("legs", []):
                leg_dist = float(leg.get("distance", 0.0))
                leg_dur = float(leg.get("duration", 0.0))
                leg_summary = leg.get("summary", "")
                legs.append(
                    RealRouteLeg(
                        summary=leg_summary,
                        distance_meters=leg_dist,
                        duration_seconds=leg_dur,
                    )
                )

            # Determine corridor summary name
            route_summary = ""
            if legs and legs[0].summary:
                route_summary = f"via {legs[0].summary}"
            elif request.origin_name and request.destination_name:
                route_summary = f"{request.origin_name} to {request.destination_name}"
            else:
                route_summary = "Primary Road Corridor" if idx == 0 else f"Alternative Route {idx}"

            parsed_routes.append(
                RealRoadRoute(
                    route_index=idx,
                    is_primary=(idx == 0),
                    summary=route_summary,
                    distance_meters=round(dist_meters, 1),
                    distance_km=round(dist_meters / 1000.0, 2),
                    duration_seconds=round(dur_seconds, 1),
                    duration_minutes=round(dur_seconds / 60.0, 1),
                    geometry=geometry,
                    legs=legs,
                    weight_name=weight_name,
                )
            )

        # Parse snapped waypoints
        waypoints_data = data.get("waypoints", [])
        origin_wp_data = waypoints_data[0] if len(waypoints_data) > 0 else {}
        dest_wp_data = waypoints_data[1] if len(waypoints_data) > 1 else {}

        # OSRM location is [lon, lat]
        origin_loc = origin_wp_data.get("location", [request.origin_lon, request.origin_lat])
        dest_loc = dest_wp_data.get("location", [request.destination_lon, request.destination_lat])

        origin_waypoint = RealRouteWaypoint(
            name=request.origin_name or origin_wp_data.get("name") or "Origin",
            lat=round(float(origin_loc[1]), 6),
            lon=round(float(origin_loc[0]), 6),
            distance_to_snapped_meters=origin_wp_data.get("distance"),
        )

        destination_waypoint = RealRouteWaypoint(
            name=request.destination_name or dest_wp_data.get("name") or "Destination",
            lat=round(float(dest_loc[1]), 6),
            lon=round(float(dest_loc[0]), 6),
            distance_to_snapped_meters=dest_wp_data.get("distance"),
        )

        return RealRouteResponse(
            origin=origin_waypoint,
            destination=destination_waypoint,
            primary_route=parsed_routes[0],
            alternative_routes=parsed_routes[1:],  # Only returned if provider yielded alternatives
            provider="osrm",
            profile="driving",
            traffic_model="standard_routability",
            attribution="Route data © OpenStreetMap contributors, OSRM Project (ODbL 1.0)",
        )

    def clear_cache(self) -> None:
        """Clear the in-memory route cache."""
        self._route_cache.clear()


real_road_service = RealRoadRoutingService()
