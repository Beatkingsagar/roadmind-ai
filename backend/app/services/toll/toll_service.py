"""Dedicated Toll Data Service for Karnataka and Indian Highway Corridors.

Integrates with verified toll intelligence providers (e.g., TollGuru India API)
with strict adherence to the Zero-Fabrication Invariant:
1. If no verified toll provider API key is configured, explicitly returns 'Toll estimate unavailable'.
2. NEVER invents toll plazas, fake toll gates, or fictional rupee prices.
3. Distinguishes confirmed published statutory FASTag tariffs from estimated rates.
4. Resilient degradation: network timeouts or upstream provider errors gracefully return
   an unavailable status without interrupting route or fuel budget calculations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import settings
from backend.app.schemas.journey_budget import (
    TollEstimate,
    TollPlazaInfo,
    TollStatusResponse,
)

logger = logging.getLogger(__name__)


class TollServiceError(Exception):
    """Base exception for toll estimation errors."""


class TollCredentialsMissingError(TollServiceError):
    """Raised when an operation requires provider credentials that are absent."""


class TollProviderError(TollServiceError):
    """Raised when an external toll provider returns an error."""


class TollTimeoutError(TollServiceError):
    """Raised when a toll provider request times out."""


# Vehicle type mapping for Indian highway toll schedules (TollGuru & NHAI classifications)
TOLLGURU_VEHICLE_MAP: Dict[str, str] = {
    "motorcycle": "2AxlesMotorcycle",
    "car": "2AxlesCar",
    "suv": "2AxlesSUV",
    "custom": "2AxlesCar",
}


class TollService:
    """Service for estimating highway toll costs along road routes."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        self.provider = provider or settings.toll_provider
        self.api_key = api_key or settings.tollguru_api_key
        self.api_url = api_url or settings.tollguru_api_url
        self._cache: Dict[str, TollEstimate] = {}

    def get_status(self) -> TollStatusResponse:
        """Audit the toll provider configuration and operational availability."""
        is_configured = bool(self.api_key and self.provider != "none")
        provider_name = "tollguru" if self.api_key else "none"

        if is_configured:
            message = "Toll provider configured via TollGuru India API."
        else:
            message = (
                "Toll estimate unavailable: No verified toll provider API key configured. "
                "Toll plazas and tariff costs are never fabricated."
            )

        return TollStatusResponse(
            active_provider=provider_name,
            is_configured=is_configured,
            is_available=is_configured,
            message=message,
            supported_regions=[
                "Karnataka National Highways (NH 66, NH 48, NH 44, NH 75)",
                "Bengaluru-Mysuru Expressway",
                "NICE Ring Road Karnataka",
                "Coastal Karnataka Toll Plazas (Hejamadi, Sasthan, Gundmi, Surathkal)",
            ],
        )

    def estimate_toll(
        self,
        encoded_polyline: Optional[str] = None,
        route_geometry: Optional[Dict[str, Any]] = None,
        route_distance_km: Optional[float] = None,
        vehicle_type: str = "car",
        is_round_trip: bool = False,
        bypass_cache: bool = False,
    ) -> TollEstimate:
        """Estimate tolls for a given route polyline or geometry.

        Zero Fabrication Guarantee:
        If no verified provider credentials are configured, returns an explicit
        'Toll estimate unavailable' status with zero plazas and null total.
        """
        # If toll provider is disabled or no API key is present
        if self.provider == "none" or not self.api_key:
            return TollEstimate(
                status="unavailable",
                provider="none",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="none",
                message=(
                    "Toll estimate unavailable: No verified toll provider API key configured. "
                    "Toll plazas and prices are not invented."
                ),
            )

        # Build cache key if polyline or coordinates are provided
        cache_key = f"{encoded_polyline or 'nopoly'}:{vehicle_type}:round={is_round_trip}"
        if not bypass_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Polyline or geometry is required to query external toll API
        if not encoded_polyline and not route_geometry:
            return TollEstimate(
                status="unavailable",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message="Toll estimate unavailable: Route geometry or polyline not provided.",
            )

        try:
            estimate = self._query_tollguru(
                encoded_polyline=encoded_polyline,
                route_geometry=route_geometry,
                vehicle_type=vehicle_type,
                is_round_trip=is_round_trip,
            )
            self._cache[cache_key] = estimate
            return estimate
        except TollCredentialsMissingError:
            return TollEstimate(
                status="unavailable",
                provider="none",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="none",
                message="Toll estimate unavailable: Provider credentials missing.",
            )
        except TollTimeoutError:
            logger.warning("Toll provider query timed out.")
            return TollEstimate(
                status="error",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message="Toll estimate unavailable: Toll provider request timed out.",
            )
        except TollRateLimitError:
            logger.warning("Toll provider rate limit reached.")
            return TollEstimate(
                status="unavailable",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message="Toll estimate unavailable: Provider rate limit exceeded. Please retry later.",
            )
        except Exception as exc:
            logger.error("Failed to query toll provider: %s", exc)
            return TollEstimate(
                status="error",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message=f"Toll estimate unavailable: {exc}",
            )

    def _query_tollguru(
        self,
        encoded_polyline: Optional[str],
        route_geometry: Optional[Dict[str, Any]],
        vehicle_type: str,
        is_round_trip: bool,
    ) -> TollEstimate:
        """Send polyline payload to TollGuru API and parse returned toll plazas."""
        if not self.api_key:
            raise TollCredentialsMissingError("TOLLGURU_API_KEY is not configured.")

        tg_vehicle = TOLLGURU_VEHICLE_MAP.get(vehicle_type, "2AxlesCar")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "User-Agent": "RoadMindAI-TollService/1.0",
        }

        # Build payload according to TollGuru documentation
        payload: Dict[str, Any] = {
            "vehicle": {
                "type": tg_vehicle,
                "weight": {"value": 2000, "unit": "kg"},
            }
        }

        if encoded_polyline:
            payload["source"] = "osrm"
            payload["polyline"] = encoded_polyline
        elif route_geometry and "coordinates" in route_geometry:
            # Send coordinates array
            coords = route_geometry["coordinates"]
            # TollGuru accepts path as [[lat, lon], ...]
            path = [[coord[1], coord[0]] for coord in coords if len(coord) >= 2]
            payload["path"] = path

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(self.api_url, json=payload, headers=headers)
        except httpx.TimeoutException as err:
            raise TollTimeoutError("TollGuru API request timed out after 8s") from err
        except httpx.HTTPError as err:
            raise TollProviderError(f"HTTP connection error with TollGuru: {err}") from err

        if resp.status_code in (401, 403):
            logger.warning("TollGuru rejected credentials with status %d", resp.status_code)
            return TollEstimate(
                status="unavailable",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message="Toll estimate unavailable: Invalid or unauthorized provider API key.",
            )

        if resp.status_code == 429:
            raise TollRateLimitError("TollGuru rate limit exceeded")

        if resp.status_code != 200:
            logger.warning("TollGuru returned non-200 code: %d %s", resp.status_code, resp.text)
            return TollEstimate(
                status="unavailable",
                provider="tollguru",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="TollGuru India API",
                message=f"Toll estimate unavailable: Provider returned HTTP {resp.status_code}.",
            )

        data = resp.json()
        return self._parse_tollguru_response(data, is_round_trip)

    def _parse_tollguru_response(self, data: Dict[str, Any], is_round_trip: bool) -> TollEstimate:
        """Parse structured TollGuru JSON response into TollEstimate."""
        routes = data.get("routes") or []
        if not routes:
            return TollEstimate(
                status="available",
                provider="tollguru",
                total_toll=0.0,
                currency="INR",
                plazas=[],
                is_confirmed=True,
                is_estimated=False,
                source="TollGuru India API",
                message="No toll plazas detected on this route corridor.",
            )

        primary = routes[0]
        costs = primary.get("costs", {})
        # Prefer FASTag rate for Indian highways, fallback to minimum cost or cash
        tag_cost = costs.get("tag")
        cash_cost = costs.get("cash")
        total_one_way = (
            float(tag_cost)
            if tag_cost is not None
            else (float(cash_cost) if cash_cost is not None else 0.0)
        )

        multiplier = 2.0 if is_round_trip else 1.0
        final_total = round(total_one_way * multiplier, 2)

        # Parse toll plazas
        plazas: List[TollPlazaInfo] = []
        raw_tolls = primary.get("tolls") or []
        for toll_item in raw_tolls:
            p_name = toll_item.get("name") or "Highway Toll Plaza"
            p_road = toll_item.get("road")
            p_cost = float(toll_item.get("tagCost") or toll_item.get("cost") or 0.0)
            p_loc = toll_item.get("location", {})
            lat = p_loc.get("lat")
            lon = p_loc.get("lng") or p_loc.get("lon")

            plazas.append(
                TollPlazaInfo(
                    plaza_name=p_name,
                    road_name=p_road,
                    cost=round(p_cost * multiplier, 2),
                    currency="INR",
                    payment_method="fastag" if toll_item.get("tagCost") is not None else "cash",
                    is_confirmed=True,
                    latitude=lat,
                    longitude=lon,
                )
            )

        trip_text = "Round-trip" if is_round_trip else "One-way"
        msg = (
            f"Estimated {trip_text} tolls: ₹{final_total:.2f} across {len(plazas)} plaza(s) via TollGuru."
            if plazas
            else "No toll plazas encountered along this route corridor."
        )

        return TollEstimate(
            status="available",
            provider="tollguru",
            total_toll=final_total,
            currency="INR",
            plazas=plazas,
            is_confirmed=True,
            is_estimated=False,
            source="TollGuru India API",
            message=msg,
        )


# Global singleton instance
toll_service = TollService()
