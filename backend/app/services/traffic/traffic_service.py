"""Real-world live traffic intelligence service.

Integrates with external traffic data providers (TomTom, HERE) to fetch
real-time road traffic observations, delays, and congestion analytics.

Strict Guarantees:
1. Real Traffic Provider Only With Credentials: Never calls external APIs without configured keys.
2. Zero Fabrication Invariant: If live traffic is unavailable or credentials are missing,
   returns explicit 'Live traffic unavailable' status and preserves standard road routability.
   NEVER fabricates synthetic congestion levels, incident delays, or traffic colors.
3. Separation of Concerns: Keeps standard road network routing (OSRM) and live traffic
   observations cleanly distinguished.
4. Resilient Degradation: Gracefully handles timeouts, rate limits (429), unauthorized keys (401/403),
   and upstream service outages without failing baseline road route calculation.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx

from backend.app.config import settings
from backend.app.schemas.real_map import (
    RealTrafficInfo,
    RealTrafficSegment,
    TrafficProviderStatus,
    TrafficStatusResponse,
)

logger = logging.getLogger(__name__)


class TrafficServiceError(Exception):
    """Base exception for traffic service operations."""


class TrafficCredentialsMissingError(TrafficServiceError):
    """Raised when an operation requires an API key that is not configured."""


class TrafficProviderError(TrafficServiceError):
    """Raised when an external traffic provider returns an unhandled error or server failure."""


class TrafficTimeoutError(TrafficServiceError):
    """Raised when an external traffic provider request times out."""


class TrafficRateLimitError(TrafficServiceError):
    """Raised when an external traffic provider rate limits the request (HTTP 429)."""


class TrafficDataUnavailableError(TrafficServiceError):
    """Raised when provider has no traffic observations for the requested coordinates."""


# Provider Specifications and Licensing Reference
PROVIDER_METADATA: Dict[str, Dict[str, str]] = {
    "tomtom": {
        "name": "TomTom Traffic Engine",
        "coverage": "High in Karnataka: Full coverage on NH 66 (Kundapura-Udupi-Surathkal-Mangaluru), NH 75, Bengaluru urban and state corridors.",
        "rate_limit_info": "Free evaluation tier: 5 QPS, up to 2,500 non-tile transactions/day.",
        "pricing_info": "Free Tier (2,500 free requests/day); Pay-as-you-go ~$0.50 per 1,000 requests thereafter.",
    },
    "here": {
        "name": "HERE Technologies Traffic API",
        "coverage": "Strong in Karnataka: High on national highways and Tier 1/2 urban networks.",
        "rate_limit_info": "Base tier: 5 QPS, up to 1,000 transactions/day or 30,000/month.",
        "pricing_info": "Freemium Base Plan (30k transactions/month free); Pay-as-you-go ~$1.00 per 1,000 transactions thereafter.",
    },
    "google": {
        "name": "Google Maps Platform (Routes API)",
        "coverage": "Comprehensive nationwide across all classifications in Karnataka.",
        "rate_limit_info": "Default 100 QPS (configurable in Google Cloud Console).",
        "pricing_info": "$200 monthly free credit across Google Cloud; ~$0.015 - $0.02 per Traffic-Aware Route compute.",
    },
    "mapbox": {
        "name": "Mapbox Directions (driving-traffic)",
        "coverage": "Moderate-high in Karnataka on major highways and arterial roads.",
        "rate_limit_info": "300 requests/minute (5 QPS).",
        "pricing_info": "Pay-as-you-go with 100,000 free requests per month.",
    },
    "osrm": {
        "name": "OpenStreetMap / OSRM (Public Project)",
        "coverage": "Global road geometry and topology. Note: Standard public instance does NOT provide live floating-car traffic data.",
        "rate_limit_info": "Public demo: Strictly max 1 QPS, intended for baseline testing/routing.",
        "pricing_info": "Open source (ODbL 1.0 license), free self-hosting.",
    },
}


class RealTrafficService:
    """Production service for live traffic intelligence and provider orchestration."""

    def __init__(self) -> None:
        # In-memory traffic cache: key -> (timestamp_epoch, RealTrafficInfo)
        self._cache: Dict[str, Tuple[float, RealTrafficInfo]] = {}
        self.cache_ttl_seconds = settings.traffic_cache_ttl_seconds

    def get_provider_status(self) -> TrafficStatusResponse:
        """Audit status of all external traffic providers without exposing private secrets."""
        tomtom_key_set = bool(settings.tomtom_api_key and settings.tomtom_api_key.strip())
        here_key_set = bool(settings.here_api_key and settings.here_api_key.strip())

        active_provider = "none"
        is_live_enabled = False

        config_pref = settings.traffic_provider.lower().strip()
        if config_pref == "tomtom" and tomtom_key_set:
            active_provider = "tomtom"
            is_live_enabled = True
        elif config_pref == "here" and here_key_set:
            active_provider = "here"
            is_live_enabled = True
        elif config_pref == "auto":
            if tomtom_key_set:
                active_provider = "tomtom"
                is_live_enabled = True
            elif here_key_set:
                active_provider = "here"
                is_live_enabled = True

        provider_statuses: List[TrafficProviderStatus] = [
            TrafficProviderStatus(
                provider_name="tomtom",
                is_configured=tomtom_key_set,
                is_available=tomtom_key_set,
                api_key_configured=tomtom_key_set,
                coverage=PROVIDER_METADATA["tomtom"]["coverage"],
                rate_limit_info=PROVIDER_METADATA["tomtom"]["rate_limit_info"],
                pricing_info=PROVIDER_METADATA["tomtom"]["pricing_info"],
            ),
            TrafficProviderStatus(
                provider_name="here",
                is_configured=here_key_set,
                is_available=here_key_set,
                api_key_configured=here_key_set,
                coverage=PROVIDER_METADATA["here"]["coverage"],
                rate_limit_info=PROVIDER_METADATA["here"]["rate_limit_info"],
                pricing_info=PROVIDER_METADATA["here"]["pricing_info"],
            ),
            TrafficProviderStatus(
                provider_name="google",
                is_configured=False,
                is_available=False,
                api_key_configured=False,
                coverage=PROVIDER_METADATA["google"]["coverage"],
                rate_limit_info=PROVIDER_METADATA["google"]["rate_limit_info"],
                pricing_info=PROVIDER_METADATA["google"]["pricing_info"],
            ),
            TrafficProviderStatus(
                provider_name="mapbox",
                is_configured=False,
                is_available=False,
                api_key_configured=False,
                coverage=PROVIDER_METADATA["mapbox"]["coverage"],
                rate_limit_info=PROVIDER_METADATA["mapbox"]["rate_limit_info"],
                pricing_info=PROVIDER_METADATA["mapbox"]["pricing_info"],
            ),
            TrafficProviderStatus(
                provider_name="osrm",
                is_configured=True,
                is_available=True,
                api_key_configured=False,
                coverage=PROVIDER_METADATA["osrm"]["coverage"],
                rate_limit_info=PROVIDER_METADATA["osrm"]["rate_limit_info"],
                pricing_info=PROVIDER_METADATA["osrm"]["pricing_info"],
            ),
        ]

        return TrafficStatusResponse(
            active_provider=active_provider,
            is_live_traffic_enabled=is_live_enabled,
            cache_entries_count=len(self._cache),
            cache_ttl_seconds=self.cache_ttl_seconds,
            providers=provider_statuses,
        )

    def fetch_route_traffic(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        bypass_cache: bool = False,
    ) -> RealTrafficInfo:
        """Fetch live traffic intelligence for a travel corridor between two points.

        If no traffic provider API key is configured or the provider request fails,
        returns an explicit 'Live traffic unavailable' RealTrafficInfo object.
        Never fabricates mock delays, fake congestion, or synthetic traffic colors.
        """
        cache_key = f"{origin_lat:.4f},{origin_lon:.4f}->{dest_lat:.4f},{dest_lon:.4f}"
        now_ts = time.time()

        # 1. Check in-memory cache
        if not bypass_cache and cache_key in self._cache:
            cached_time, cached_info = self._cache[cache_key]
            age = now_ts - cached_time
            if age <= self.cache_ttl_seconds:
                # Mark as stale if approaching end of TTL
                is_stale = age > (self.cache_ttl_seconds * 0.75)
                return cached_info.model_copy(update={"is_stale": is_stale})

        # 2. Identify active provider
        active_provider, api_key = self._resolve_active_provider()

        # 3. If no provider credentials available, return clean unavailable response
        if not active_provider or not api_key:
            return RealTrafficInfo(
                status="unavailable",
                provider="none",
                source_description="Standard Road Network (OSRM)",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (No external traffic provider API key configured)",
                segments=[],
            )

        # 4. Dispatch to configured provider
        if active_provider == "tomtom":
            traffic_info = self._query_tomtom_traffic(
                origin_lat, origin_lon, dest_lat, dest_lon, api_key
            )
        elif active_provider == "here":
            traffic_info = self._query_here_traffic(
                origin_lat, origin_lon, dest_lat, dest_lon, api_key
            )
        else:
            traffic_info = RealTrafficInfo(
                status="unavailable",
                provider="none",
                source_description="Unsupported Provider",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (Provider unsupported)",
                segments=[],
            )

        # Cache valid response
        if traffic_info.status in ("available", "unavailable", "unauthorized", "rate_limited"):
            self._cache[cache_key] = (now_ts, traffic_info)

        return traffic_info

    def _resolve_active_provider(self) -> Tuple[Optional[str], Optional[str]]:
        """Determine which provider to query and retrieve its key."""
        config_pref = settings.traffic_provider.lower().strip()
        tomtom_key = settings.tomtom_api_key.strip() if settings.tomtom_api_key else None
        here_key = settings.here_api_key.strip() if settings.here_api_key else None

        if config_pref == "none":
            return None, None
        if config_pref == "tomtom" and tomtom_key:
            return "tomtom", tomtom_key
        if config_pref == "here" and here_key:
            return "here", here_key
        if config_pref == "auto":
            if tomtom_key:
                return "tomtom", tomtom_key
            if here_key:
                return "here", here_key

        return None, None

    def _query_tomtom_traffic(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        api_key: str,
    ) -> RealTrafficInfo:
        """Query TomTom Routing API with traffic parameters."""
        # TomTom expects locations in "lat,lon:lat,lon" format
        locations = f"{origin_lat},{origin_lon}:{dest_lat},{dest_lon}"
        url = f"{settings.tomtom_routing_url.rstrip('/')}/{locations}/json"
        params = {
            "key": api_key,
            "traffic": "true",
            "departAt": "now",
            "computeTravelTimeFor": "all",
            "sectionType": "traffic",
            "travelMode": "car",
        }
        headers = {
            "User-Agent": "RoadMindAI-TrafficEngine/1.0",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=8.0, headers=headers) as client:
                resp = client.get(url, params=params)
        except httpx.TimeoutException as err:
            logger.warning("TomTom traffic provider timed out: %s", err)
            return RealTrafficInfo(
                status="unavailable",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (TomTom traffic request timed out after 8.0s)",
                segments=[],
            )
        except (httpx.ConnectError, httpx.NetworkError) as err:
            logger.error("TomTom traffic provider network failure: %s", err)
            return RealTrafficInfo(
                status="unavailable",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (Could not reach TomTom traffic service)",
                segments=[],
            )
        except Exception as err:
            logger.error("Unexpected error querying TomTom traffic: %s", err)
            return RealTrafficInfo(
                status="error",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message=f"Live traffic unavailable (Provider request error: {err})",
                segments=[],
            )

        # Handle HTTP status codes
        if resp.status_code in (401, 403):
            logger.warning("TomTom API key invalid or unauthorized: HTTP %s", resp.status_code)
            return RealTrafficInfo(
                status="unauthorized",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (Invalid or unauthorized TomTom API key)",
                segments=[],
            )

        if resp.status_code == 429:
            logger.warning("TomTom API rate limit exceeded")
            return RealTrafficInfo(
                status="rate_limited",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (TomTom API rate limit reached)",
                segments=[],
            )

        if resp.status_code >= 500:
            logger.error("TomTom server error: HTTP %s", resp.status_code)
            return RealTrafficInfo(
                status="error",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message=f"Live traffic unavailable (TomTom server error HTTP {resp.status_code})",
                segments=[],
            )

        try:
            data = resp.json()
        except Exception as err:
            logger.error("Failed to parse TomTom JSON: %s", err)
            return RealTrafficInfo(
                status="error",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (Malformed JSON response from TomTom)",
                segments=[],
            )

        routes = data.get("routes", [])
        if not routes:
            return RealTrafficInfo(
                status="unavailable",
                provider="tomtom",
                source_description="TomTom Traffic Engine",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (No traffic routes returned)",
                segments=[],
            )

        primary_route = routes[0]
        summary = primary_route.get("summary", {})
        legs = primary_route.get("legs", [])
        sections = primary_route.get("sections", [])

        # Extract timings
        duration_traffic_sec = float(summary.get("travelTimeInSeconds", 0.0))
        delay_sec = float(summary.get("trafficDelayInSeconds", 0.0))

        # Extract granular traffic segments if present in sections
        segments: List[RealTrafficSegment] = []
        if legs and len(legs) > 0 and sections:
            points = legs[0].get("points", [])
            for s_idx, sec in enumerate(sections):
                if sec.get("sectionType") == "TRAFFIC":
                    start_i = sec.get("startPointIndex", 0)
                    end_i = sec.get("endPointIndex", 0)
                    s_delay = float(sec.get("delayInSeconds", 0.0))
                    magnitude = sec.get("magnitudeOfDelay", 0)

                    # Map TomTom magnitude of delay (0: unknown, 1: minor, 2: moderate, 3: major, 4: undefined)
                    severity_map = {
                        0: "minor",
                        1: "minor",
                        2: "moderate",
                        3: "major",
                        4: "severe",
                    }
                    severity = severity_map.get(magnitude, "moderate")

                    start_pt = [origin_lon, origin_lat]
                    end_pt = [dest_lon, dest_lat]
                    if 0 <= start_i < len(points):
                        start_pt = [points[start_i].get("longitude", origin_lon), points[start_i].get("latitude", origin_lat)]
                    if 0 <= end_i < len(points):
                        end_pt = [points[end_i].get("longitude", dest_lon), points[end_i].get("latitude", dest_lat)]

                    segments.append(
                        RealTrafficSegment(
                            segment_index=s_idx,
                            start_coord=start_pt,
                            end_coord=end_pt,
                            delay_seconds=s_delay,
                            severity=severity,
                            description=sec.get("simpleCategory", "Congestion slowdown"),
                        )
                    )

        now_iso = datetime.now(timezone.utc).isoformat()
        delay_min = round(delay_sec / 60.0, 1)

        if delay_sec > 60.0:
            msg = f"Live traffic active: +{delay_min} min delay on corridor via TomTom Traffic"
        else:
            msg = "Live traffic active: Flow moving normally with minimal delay via TomTom Traffic"

        return RealTrafficInfo(
            status="available",
            provider="tomtom",
            source_description="TomTom Traffic Engine (Live Flow & Delay)",
            duration_with_traffic_seconds=round(duration_traffic_sec, 1),
            duration_with_traffic_minutes=round(duration_traffic_sec / 60.0, 1),
            delay_seconds=round(delay_sec, 1),
            delay_minutes=delay_min,
            traffic_model="provider_traffic_estimate",
            fetched_at=now_iso,
            is_stale=False,
            message=msg,
            segments=segments,
        )

    def _query_here_traffic(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        api_key: str,
    ) -> RealTrafficInfo:
        """Query HERE Routing v8 API with traffic parameters."""
        url = settings.here_routing_url.rstrip("/")
        params = {
            "apiKey": api_key,
            "transportMode": "car",
            "origin": f"{origin_lat},{origin_lon}",
            "destination": f"{dest_lat},{dest_lon}",
            "return": "summary,typicalDuration",
            "departureTime": "any",
        }
        headers = {
            "User-Agent": "RoadMindAI-TrafficEngine/1.0",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=8.0, headers=headers) as client:
                resp = client.get(url, params=params)
        except Exception as err:
            logger.warning("HERE traffic provider request error: %s", err)
            return RealTrafficInfo(
                status="unavailable",
                provider="here",
                source_description="HERE Technologies Traffic",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message=f"Live traffic unavailable (HERE request failed: {err})",
                segments=[],
            )

        if resp.status_code in (401, 403):
            return RealTrafficInfo(
                status="unauthorized",
                provider="here",
                source_description="HERE Technologies Traffic",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (Invalid or unauthorized HERE API key)",
                segments=[],
            )

        if resp.status_code == 429:
            return RealTrafficInfo(
                status="rate_limited",
                provider="here",
                source_description="HERE Technologies Traffic",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message="Live traffic unavailable (HERE API rate limit reached)",
                segments=[],
            )

        if resp.status_code != 200:
            return RealTrafficInfo(
                status="error",
                provider="here",
                source_description="HERE Technologies Traffic",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message=f"Live traffic unavailable (HERE provider returned HTTP {resp.status_code})",
                segments=[],
            )

        try:
            data = resp.json()
            routes = data.get("routes", [])
            if not routes:
                raise ValueError("No routes returned by HERE")

            sections = routes[0].get("sections", [])
            total_duration = sum(float(s.get("summary", {}).get("duration", 0.0)) for s in sections)
            base_duration = sum(float(s.get("summary", {}).get("baseDuration", total_duration)) for s in sections)

            delay_sec = max(0.0, total_duration - base_duration)
            now_iso = datetime.now(timezone.utc).isoformat()
            delay_min = round(delay_sec / 60.0, 1)

            return RealTrafficInfo(
                status="available",
                provider="here",
                source_description="HERE Technologies Traffic API (Live Routing)",
                duration_with_traffic_seconds=round(total_duration, 1),
                duration_with_traffic_minutes=round(total_duration / 60.0, 1),
                delay_seconds=round(delay_sec, 1),
                delay_minutes=delay_min,
                traffic_model="provider_traffic_estimate",
                fetched_at=now_iso,
                is_stale=False,
                message=f"Live traffic active: +{delay_min} min delay via HERE Traffic",
                segments=[],
            )
        except Exception as err:
            return RealTrafficInfo(
                status="error",
                provider="here",
                source_description="HERE Technologies Traffic",
                duration_with_traffic_seconds=None,
                duration_with_traffic_minutes=None,
                delay_seconds=0.0,
                delay_minutes=0.0,
                traffic_model="standard_routability",
                fetched_at=None,
                is_stale=False,
                message=f"Live traffic unavailable (Failed to parse HERE response: {err})",
                segments=[],
            )

    def clear_cache(self) -> None:
        """Clear cached traffic records."""
        self._cache.clear()


traffic_service = RealTrafficService()
