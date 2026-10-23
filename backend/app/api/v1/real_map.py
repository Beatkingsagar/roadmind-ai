"""Real-World Map Geocoding and Place Search API endpoints."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.real_map import (
    PlaceSearchResponse,
    RealRouteRequest,
    RealRouteResponse,
)
from backend.app.services.geocoding import (
    GeocodingProviderError,
    GeocodingRateLimitError,
    GeocodingTimeoutError,
    InvalidQueryError,
    geocoding_service,
)
from backend.app.services.routing import (
    InvalidRouteCoordinatesError,
    NoRouteFoundError,
    RoutingProviderError,
    RoutingRateLimitError,
    RoutingTimeoutError,
    real_road_service,
)

router = APIRouter(prefix="/real-map", tags=["Real Map Geocoding & Routing"])


@router.get(
    "/search",
    response_model=PlaceSearchResponse,
    summary="Search real-world geographic places with validated coordinates",
    description=(
        "Geocodes real-world locations (especially Coastal Karnataka: Kundapura, Udupi, "
        "Surathkal, Mangaluru, etc.). Returns structured location metadata with verified WGS84 "
        "coordinates, disambiguating cached landmarks from live OSM Nominatim results."
    ),
)
def search_places(
    q: str = Query(..., description="Search query string for location (e.g., 'Kundapura', 'Mangaluru')"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results to return"),
    bypass_cache: bool = Query(False, description="Set True to bypass local verified cache"),
) -> PlaceSearchResponse:
    """Execute real-place search."""
    try:
        return geocoding_service.search_places(
            query=q,
            limit=limit,
            bypass_cache=bypass_cache,
        )
    except InvalidQueryError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except GeocodingTimeoutError as err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(err),
        ) from err
    except GeocodingRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
        ) from err
    except GeocodingProviderError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred during place geocoding.",
        ) from exc


@router.post(
    "/route",
    response_model=RealRouteResponse,
    summary="Calculate real-world road route between geographic coordinates",
    description=(
        "Calculates drivable road route between origin and destination coordinates (e.g., Kundapura to Mangaluru). "
        "Returns GeoJSON LineString geometry, road distance in meters/kilometers, estimated duration, "
        "and alternative routes only when returned by the routing provider. Clearly distinguishes standard road routability "
        "from live traffic or synthetic incident simulations."
    ),
)
def calculate_real_route(
    payload: RealRouteRequest,
    bypass_cache: bool = Query(False, description="Set True to bypass route cache and query provider"),
) -> RealRouteResponse:
    """Calculate driving route between origin and destination."""
    try:
        return real_road_service.calculate_route(payload, bypass_cache=bypass_cache)
    except InvalidRouteCoordinatesError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except NoRouteFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except RoutingTimeoutError as err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(err),
        ) from err
    except RoutingRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
        ) from err
    except RoutingProviderError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred during road routing calculation.",
        ) from exc


@router.get(
    "/route",
    response_model=RealRouteResponse,
    summary="Calculate real-world road route via query parameters",
    description="Convenience GET endpoint to calculate road routing between query-specified WGS84 coordinates.",
)
def get_real_route(
    origin_lat: float = Query(..., ge=-90.0, le=90.0, description="Origin latitude in WGS84"),
    origin_lon: float = Query(..., ge=-180.0, le=180.0, description="Origin longitude in WGS84"),
    destination_lat: float = Query(..., ge=-90.0, le=90.0, description="Destination latitude in WGS84"),
    destination_lon: float = Query(..., ge=-180.0, le=180.0, description="Destination longitude in WGS84"),
    origin_name: Optional[str] = Query(None, description="Optional human-readable label for origin"),
    destination_name: Optional[str] = Query(None, description="Optional human-readable label for destination"),
    alternatives: bool = Query(True, description="Request alternative routes if provider returns them"),
    bypass_cache: bool = Query(False, description="Set True to bypass route cache and query provider"),
) -> RealRouteResponse:
    """Convenience GET endpoint for calculating road route."""
    request = RealRouteRequest(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        origin_name=origin_name,
        destination_name=destination_name,
        alternatives=alternatives,
    )
    return calculate_real_route(payload=request, bypass_cache=bypass_cache)
