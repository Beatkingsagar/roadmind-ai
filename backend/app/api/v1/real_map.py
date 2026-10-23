"""Real-World Map Geocoding and Place Search API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.real_map import PlaceSearchResponse
from backend.app.services.geocoding import (
    GeocodingProviderError,
    GeocodingRateLimitError,
    GeocodingTimeoutError,
    InvalidQueryError,
    geocoding_service,
)

router = APIRouter(prefix="/real-map", tags=["Real Map Geocoding"])


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
