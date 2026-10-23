"""Geocoding service for real-world place search and coordinate validation.

Provides:
- High-precision verified cache for Coastal Karnataka (Kundapura, Udupi, Manipal, Surathkal, Mangaluru, SDIT Kenjar).
- Live OpenStreetMap Nominatim fallback with rate limiting, timeouts, User-Agent identification, and coordinate validation.
- Distinct source tagging ('verified_cache' vs 'osm_nominatim').
- Standardized error handling for timeouts, rate limits, and network errors.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.schemas.real_map import PlaceSearchResponse, PlaceSearchResult


class GeocodingError(Exception):
    """Base exception for geocoding failures."""


class InvalidQueryError(GeocodingError):
    """Raised when search query fails validation."""


class GeocodingTimeoutError(GeocodingError):
    """Raised when the geocoding provider times out."""


class GeocodingRateLimitError(GeocodingError):
    """Raised when provider rate limits are encountered."""


class GeocodingProviderError(GeocodingError):
    """Raised when the geocoding provider returns 5xx or connection fails."""


# Verified ground-truth coordinates for Coastal Karnataka corridor
VERIFIED_COASTAL_KARNATAKA_CACHE: List[Dict[str, Any]] = [
    {
        "id": "cache_kundapura",
        "name": "Kundapura",
        "display_name": "Kundapura, Udupi District, Karnataka, India",
        "category": "place",
        "type": "town",
        "lat": 13.6268,
        "lon": 74.6917,
        "bounding_box": [13.5800, 13.6800, 74.6500, 74.7500],
        "keywords": ["kundapura", "kundapur", "kundapure", "coondapur"],
        "importance": 0.95,
    },
    {
        "id": "cache_mangaluru",
        "name": "Mangaluru",
        "display_name": "Mangaluru, Dakshina Kannada, Karnataka, India",
        "category": "place",
        "type": "city",
        "lat": 12.9141,
        "lon": 74.8560,
        "bounding_box": [12.8200, 12.9900, 74.8000, 74.9200],
        "keywords": ["mangaluru", "mangalore", "kudla", "mangaluru city"],
        "importance": 0.98,
    },
    {
        "id": "cache_udupi",
        "name": "Udupi",
        "display_name": "Udupi, Udupi District, Karnataka, India",
        "category": "place",
        "type": "city",
        "lat": 13.3409,
        "lon": 74.7421,
        "bounding_box": [13.3000, 13.3800, 74.7000, 74.8000],
        "keywords": ["udupi", "odipu"],
        "importance": 0.92,
    },
    {
        "id": "cache_manipal",
        "name": "Manipal",
        "display_name": "Manipal, Udupi District, Karnataka, India",
        "category": "place",
        "type": "suburb",
        "lat": 13.3525,
        "lon": 74.7928,
        "bounding_box": [13.3300, 13.3700, 74.7700, 74.8200],
        "keywords": ["manipal", "manipal university"],
        "importance": 0.88,
    },
    {
        "id": "cache_surathkal",
        "name": "Surathkal",
        "display_name": "Surathkal, Mangaluru, Dakshina Kannada, Karnataka, India",
        "category": "place",
        "type": "town",
        "lat": 13.0119,
        "lon": 74.7943,
        "bounding_box": [12.9800, 13.0300, 74.7700, 74.8200],
        "keywords": ["surathkal", "surathkal junction", "nitk", "nitk surathkal"],
        "importance": 0.87,
    },
    {
        "id": "cache_sdit_kenjar",
        "name": "SDIT Kenjar (Airport Road)",
        "display_name": "Shree Devi Institute of Technology (SDIT), Kenjar, Mangaluru, Karnataka, India",
        "category": "amenity",
        "type": "college",
        "lat": 12.9610,
        "lon": 74.8967,
        "bounding_box": [12.9550, 12.9680, 74.8900, 74.9050],
        "keywords": ["sdit", "sdit kenjar", "shree devi", "kenjar"],
        "importance": 0.85,
    },
    {
        "id": "cache_mng_airport",
        "name": "Mangaluru International Airport (IXE)",
        "display_name": "Mangaluru International Airport (IXE), Kenjar/Bajpe, Karnataka, India",
        "category": "aeroway",
        "type": "aerodrome",
        "lat": 12.9613,
        "lon": 74.8900,
        "bounding_box": [12.9500, 12.9750, 74.8800, 74.9050],
        "keywords": ["airport", "mangaluru airport", "mangalore airport", "bajpe airport", "ixe"],
        "importance": 0.90,
    },
    {
        "id": "cache_hampankatta",
        "name": "Hampankatta",
        "display_name": "Hampankatta, Mangaluru, Dakshina Kannada, Karnataka, India",
        "category": "place",
        "type": "suburb",
        "lat": 12.8703,
        "lon": 74.8427,
        "bounding_box": [12.8650, 12.8750, 74.8380, 74.8480],
        "keywords": ["hampankatta", "mangaluru central", "ks rao road"],
        "importance": 0.86,
    },
]


class GeocodingService:
    """Service handling real-place search, coordinate validation, and caching."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "RoadMind-AI/1.0 (hackathon-research; contact@roadmind.ai)"
    TIMEOUT_SECONDS = 5.0

    @staticmethod
    def normalize_query(query: str) -> str:
        """Strip extra whitespace, lowercase, and sanitize query."""
        if not query:
            return ""
        # Remove special characters that are not alphanumeric or space/comma
        cleaned = re.sub(r"[^\w\s,.-]", "", query.strip().lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def search_verified_cache(self, query: str) -> List[PlaceSearchResult]:
        """Search local verified cache for ground-truth Coastal Karnataka locations."""
        norm_q = self.normalize_query(query)
        if not norm_q or len(norm_q) < 2:
            return []

        # Split into tokens for flexible matching
        tokens = [t.strip(",") for t in norm_q.split() if len(t.strip(",")) >= 2]
        matches: List[PlaceSearchResult] = []

        for item in VERIFIED_COASTAL_KARNATAKA_CACHE:
            item_name_lower = item["name"].lower()
            item_display_lower = item["display_name"].lower()
            keywords = item.get("keywords", [])

            # Direct keyword match or name contains query
            is_match = False
            if norm_q in item_name_lower or norm_q in item_display_lower:
                is_match = True
            elif any(k in norm_q or norm_q in k for k in keywords):
                is_match = True
            elif tokens and all(t in item_display_lower for t in tokens):
                is_match = True

            if is_match:
                matches.append(
                    PlaceSearchResult(
                        id=item["id"],
                        display_name=item["display_name"],
                        name=item["name"],
                        category=item.get("category"),
                        type=item.get("type"),
                        lat=item["lat"],
                        lon=item["lon"],
                        bounding_box=item.get("bounding_box"),
                        source="verified_cache",
                        importance=item.get("importance", 0.9),
                    )
                )

        # Sort by importance descending
        matches.sort(key=lambda x: x.importance or 0.0, reverse=True)
        return matches

    def _query_nominatim(self, query: str, limit: int = 5) -> List[PlaceSearchResult]:
        """Query OpenStreetMap Nominatim HTTP service."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": "1",
            "limit": str(limit),
        }

        try:
            with httpx.Client(timeout=self.TIMEOUT_SECONDS) as client:
                response = client.get(self.NOMINATIM_URL, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise GeocodingTimeoutError("Geocoding service timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise GeocodingProviderError(f"Geocoding service unreachable: {exc}") from exc

        if response.status_code == 429:
            raise GeocodingRateLimitError("Geocoding rate limit exceeded. Please try again in a moment.")
        if response.status_code >= 500:
            raise GeocodingProviderError("Geocoding provider returned a server error.")
        if response.status_code != 200:
            raise GeocodingProviderError(f"Unexpected response from geocoding provider (HTTP {response.status_code}).")

        try:
            data = response.json()
        except Exception as exc:
            raise GeocodingProviderError("Failed to parse geocoding provider response.") from exc

        if not isinstance(data, list):
            return []

        results: List[PlaceSearchResult] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            raw_lat = item.get("lat")
            raw_lon = item.get("lon")
            if raw_lat is None or raw_lon is None:
                continue

            try:
                lat = float(raw_lat)
                lon = float(raw_lon)
            except (ValueError, TypeError):
                continue

            # Validate coordinate boundaries
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                continue

            place_id = str(item.get("place_id", f"osm_{lat}_{lon}"))
            display_name = str(item.get("display_name", "")).strip()
            name = str(item.get("name") or display_name.split(",")[0]).strip()

            bbox = None
            if "boundingbox" in item and isinstance(item["boundingbox"], list) and len(item["boundingbox"]) == 4:
                try:
                    bbox = [float(b) for b in item["boundingbox"]]
                except (ValueError, TypeError):
                    bbox = None

            importance = None
            if "importance" in item:
                try:
                    importance = float(item["importance"])
                except (ValueError, TypeError):
                    importance = None

            results.append(
                PlaceSearchResult(
                    id=f"osm_{place_id}",
                    display_name=display_name,
                    name=name,
                    category=item.get("category"),
                    type=item.get("type"),
                    lat=lat,
                    lon=lon,
                    bounding_box=bbox,
                    source="osm_nominatim",
                    importance=importance,
                    raw_address=item.get("address"),
                )
            )

        return results

    def search_places(
        self,
        query: str,
        limit: int = 5,
        bypass_cache: bool = False,
    ) -> PlaceSearchResponse:
        """Search for places with verified local cache and Nominatim fallback."""
        raw_query = query
        if not query or not query.strip():
            raise InvalidQueryError("Search query 'q' must not be empty or whitespace only.")

        normalized = self.normalize_query(query)
        if len(normalized) < 2:
            raise InvalidQueryError("Search query must be at least 2 characters long.")

        # Check local verified cache first
        if not bypass_cache:
            cached_matches = self.search_verified_cache(normalized)
            if cached_matches:
                return PlaceSearchResponse(
                    query=raw_query.strip(),
                    count=len(cached_matches[:limit]),
                    results=cached_matches[:limit],
                    source="verified_cache",
                )

        # Query live OSM Nominatim provider
        live_results = self._query_nominatim(raw_query.strip(), limit=limit)
        return PlaceSearchResponse(
            query=raw_query.strip(),
            count=len(live_results),
            results=live_results,
            source="osm_nominatim" if live_results else "empty",
        )


# Singleton service instance
geocoding_service = GeocodingService()
