"""Unit tests for RealRoadRoutingService and OSRM Road Routing."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_workspace = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

import httpx
import pytest

from backend.app.schemas.real_map import RealRouteRequest
from backend.app.services.routing.real_road_service import (
    InvalidRouteCoordinatesError,
    NoRouteFoundError,
    RealRoadRoutingService,
    RoutingProviderError,
    RoutingRateLimitError,
    RoutingTimeoutError,
)

# Realistic sample OSRM fixture: Kundapura (13.6268, 74.6917) to Mangaluru (12.9141, 74.8560)
SAMPLE_OSRM_KUNDAPURA_MANGALURU = {
    "code": "Ok",
    "routes": [
        {
            "geometry": {
                "coordinates": [
                    [74.6917, 13.6268],
                    [74.7421, 13.3409],  # Udupi
                    [74.7943, 13.0119],  # Surathkal
                    [74.8560, 12.9141],  # Mangaluru
                ],
                "type": "LineString",
            },
            "legs": [
                {
                    "summary": "NH 66",
                    "weight": 4671.2,
                    "duration": 4671.6,
                    "distance": 91900.5,
                    "steps": [],
                }
            ],
            "weight_name": "routability",
            "weight": 4671.2,
            "duration": 4671.6,
            "distance": 91900.5,
        }
    ],
    "waypoints": [
        {
            "hint": "hint_origin",
            "distance": 8.5,
            "name": "Kundapura Main Road",
            "location": [74.6917, 13.6268],
        },
        {
            "hint": "hint_destination",
            "distance": 12.2,
            "name": "KSR Road",
            "location": [74.8560, 12.9141],
        },
    ],
}

# Sample with an alternative route
SAMPLE_OSRM_WITH_ALTERNATIVE = {
    "code": "Ok",
    "routes": [
        {
            "geometry": {
                "coordinates": [[74.6917, 13.6268], [74.7421, 13.3409], [74.8560, 12.9141]],
                "type": "LineString",
            },
            "legs": [{"summary": "NH 66", "duration": 4671.6, "distance": 91900.5}],
            "weight_name": "routability",
            "duration": 4671.6,
            "distance": 91900.5,
        },
        {
            "geometry": {
                "coordinates": [[74.6917, 13.6268], [74.7928, 13.3525], [74.8560, 12.9141]],
                "type": "LineString",
            },
            "legs": [{"summary": "via Manipal / Karkala State Highway", "duration": 5420.0, "distance": 99400.0}],
            "weight_name": "routability",
            "duration": 5420.0,
            "distance": 99400.0,
        },
    ],
    "waypoints": [
        {"name": "Kundapura", "location": [74.6917, 13.6268], "distance": 5.0},
        {"name": "Mangaluru", "location": [74.8560, 12.9141], "distance": 10.0},
    ],
}

# Reverse direction sample: Mangaluru to Kundapura
SAMPLE_OSRM_MANGALURU_KUNDAPURA = {
    "code": "Ok",
    "routes": [
        {
            "geometry": {
                "coordinates": [
                    [74.8560, 12.9141],
                    [74.7943, 13.0119],
                    [74.7421, 13.3409],
                    [74.6917, 13.6268],
                ],
                "type": "LineString",
            },
            "legs": [{"summary": "NH 66", "duration": 4925.0, "distance": 91520.0}],
            "weight_name": "routability",
            "duration": 4925.0,
            "distance": 91520.0,
        }
    ],
    "waypoints": [
        {"name": "Mangaluru", "location": [74.8560, 12.9141], "distance": 10.0},
        {"name": "Kundapura", "location": [74.6917, 13.6268], "distance": 5.0},
    ],
}

# Second valid pair: Udupi to Surathkal
SAMPLE_OSRM_UDUPI_SURATHKAL = {
    "code": "Ok",
    "routes": [
        {
            "geometry": {
                "coordinates": [
                    [74.7421, 13.3409],
                    [74.7943, 13.0119],
                ],
                "type": "LineString",
            },
            "legs": [{"summary": "NH 66", "duration": 1860.0, "distance": 35800.0}],
            "weight_name": "routability",
            "duration": 1860.0,
            "distance": 35800.0,
        }
    ],
    "waypoints": [
        {"name": "Udupi", "location": [74.7421, 13.3409], "distance": 4.0},
        {"name": "Surathkal", "location": [74.7943, 13.0119], "distance": 6.0},
    ],
}


@pytest.fixture
def service():
    srv = RealRoadRoutingService()
    srv.clear_cache()
    return srv


def test_kundapura_to_mangaluru_routing(service):
    """Test road routing from Kundapura to Mangaluru along NH 66 corridor."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
        origin_name="Kundapura",
        destination_name="Mangaluru",
    )

    with patch.object(service, "_query_osrm", return_value=SAMPLE_OSRM_KUNDAPURA_MANGALURU) as mock_query:
        resp = service.calculate_route(req)

        assert mock_query.called
        assert resp.origin.name == "Kundapura"
        assert resp.destination.name == "Mangaluru"
        assert resp.provider == "osrm"
        assert resp.traffic_model == "standard_routability"
        assert "OpenStreetMap" in resp.attribution

        primary = resp.primary_route
        assert primary.is_primary is True
        assert primary.route_index == 0
        assert "NH 66" in primary.summary
        assert pytest.approx(primary.distance_km, abs=0.1) == 91.90
        assert pytest.approx(primary.duration_minutes, abs=0.2) == 77.9
        assert primary.geometry["type"] == "LineString"
        assert len(primary.geometry["coordinates"]) == 4

        # No alternative was returned by the provider, so alternative_routes must be empty
        assert len(resp.alternative_routes) == 0


def test_reverse_direction_mangaluru_to_kundapura(service):
    """Test reverse direction routing from Mangaluru to Kundapura."""
    req = RealRouteRequest(
        origin_lat=12.9141,
        origin_lon=74.8560,
        destination_lat=13.6268,
        destination_lon=74.6917,
        origin_name="Mangaluru",
        destination_name="Kundapura",
    )

    with patch.object(service, "_query_osrm", return_value=SAMPLE_OSRM_MANGALURU_KUNDAPURA):
        resp = service.calculate_route(req)

        assert resp.origin.name == "Mangaluru"
        assert resp.destination.name == "Kundapura"
        assert pytest.approx(resp.primary_route.distance_km, abs=0.1) == 91.52
        assert pytest.approx(resp.primary_route.duration_minutes, abs=0.2) == 82.1
        assert resp.primary_route.geometry["type"] == "LineString"


def test_second_valid_pair_udupi_to_surathkal(service):
    """Test a second distinct Coastal Karnataka pair: Udupi to Surathkal."""
    req = RealRouteRequest(
        origin_lat=13.3409,
        origin_lon=74.7421,
        destination_lat=13.0119,
        destination_lon=74.7943,
        origin_name="Udupi",
        destination_name="Surathkal",
    )

    with patch.object(service, "_query_osrm", return_value=SAMPLE_OSRM_UDUPI_SURATHKAL):
        resp = service.calculate_route(req)

        assert resp.origin.name == "Udupi"
        assert resp.destination.name == "Surathkal"
        assert pytest.approx(resp.primary_route.distance_km, abs=0.1) == 35.80
        assert pytest.approx(resp.primary_route.duration_minutes, abs=0.2) == 31.0


def test_alternative_routes_returned_only_when_provider_provides_them(service):
    """Verify alternative routes are parsed when provider returns them and NOT fabricated."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
        alternatives=True,
    )

    with patch.object(service, "_query_osrm", return_value=SAMPLE_OSRM_WITH_ALTERNATIVE):
        resp = service.calculate_route(req)

        assert resp.primary_route.is_primary is True
        assert len(resp.alternative_routes) == 1
        alt = resp.alternative_routes[0]
        assert alt.is_primary is False
        assert alt.route_index == 1
        assert pytest.approx(alt.distance_km, abs=0.1) == 99.40
        assert pytest.approx(alt.duration_minutes, abs=0.2) == 90.3


def test_identical_origin_and_destination_rejected(service):
    """Reject route request where origin and destination coordinates are identical."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=13.6268,
        destination_lon=74.6917,
    )
    with pytest.raises(InvalidRouteCoordinatesError, match="too close or identical"):
        service.calculate_route(req)


def test_out_of_bounds_coordinates_rejected(service):
    """Reject coordinates out of valid WGS84 range."""
    with pytest.raises(Exception):
        RealRouteRequest(
            origin_lat=95.0,  # invalid latitude > 90
            origin_lon=74.0,
            destination_lat=12.0,
            destination_lon=74.0,
        )


def test_no_route_found_raises_exception(service):
    """Handle OSRM 'NoRoute' code gracefully with NoRouteFoundError."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
    )
    with patch.object(service, "_query_osrm", side_effect=NoRouteFoundError("No road route found")):
        with pytest.raises(NoRouteFoundError, match="No road route found"):
            service.calculate_route(req)


def test_osrm_timeout_handling(service):
    """Handle provider network timeout with RoutingTimeoutError."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
    )
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(RoutingTimeoutError, match="timed out"):
            service.calculate_route(req, bypass_cache=True)


def test_osrm_rate_limit_handling(service):
    """Handle HTTP 429 rate limit with RoutingRateLimitError."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(RoutingRateLimitError, match="rate limit exceeded"):
            service.calculate_route(req, bypass_cache=True)


def test_osrm_server_error_handling(service):
    """Handle HTTP 502/500 provider error with RoutingProviderError."""
    req = RealRouteRequest(
        origin_lat=13.6268,
        origin_lon=74.6917,
        destination_lat=12.9141,
        destination_lon=74.8560,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(RoutingProviderError, match="HTTP 502"):
            service.calculate_route(req, bypass_cache=True)
