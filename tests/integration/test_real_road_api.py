"""Integration tests for the Real-World Road Routing API (/api/v1/real-map/route)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_workspace = Path(__file__).resolve().parent.parent.parent
_pkg_dir = _workspace / ".python_packages"
if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.routing.real_road_service import (
    NoRouteFoundError,
    RoutingProviderError,
    RoutingRateLimitError,
    RoutingTimeoutError,
    real_road_service,
)

SAMPLE_OSRM_KUNDAPURA_MANGALURU = {
    "code": "Ok",
    "routes": [
        {
            "geometry": {
                "coordinates": [
                    [74.6917, 13.6268],
                    [74.7421, 13.3409],
                    [74.7943, 13.0119],
                    [74.8560, 12.9141],
                ],
                "type": "LineString",
            },
            "legs": [{"summary": "NH 66", "duration": 4671.6, "distance": 91900.5}],
            "weight_name": "routability",
            "duration": 4671.6,
            "distance": 91900.5,
        }
    ],
    "waypoints": [
        {"name": "Kundapura", "location": [74.6917, 13.6268], "distance": 8.0},
        {"name": "Mangaluru", "location": [74.8560, 12.9141], "distance": 12.0},
    ],
}

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


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def clean_route_cache():
    real_road_service.clear_cache()
    yield
    real_road_service.clear_cache()


def test_api_post_route_kundapura_to_mangaluru(client):
    """POST /api/v1/real-map/route returns verified road geometry and metrics."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
        "origin_name": "Kundapura",
        "destination_name": "Mangaluru",
        "alternatives": True,
    }

    with patch.object(real_road_service, "_query_osrm", return_value=SAMPLE_OSRM_KUNDAPURA_MANGALURU):
        resp = client.post("/api/v1/real-map/route", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["origin"]["name"] == "Kundapura"
        assert data["destination"]["name"] == "Mangaluru"
        assert data["provider"] == "osrm"
        assert data["traffic_model"] == "standard_routability"
        assert "OpenStreetMap" in data["attribution"]

        primary = data["primary_route"]
        assert primary["is_primary"] is True
        assert primary["route_index"] == 0
        assert "NH 66" in primary["summary"]
        assert pytest.approx(primary["distance_km"], abs=0.1) == 91.90
        assert pytest.approx(primary["duration_minutes"], abs=0.2) == 77.9
        assert primary["geometry"]["type"] == "LineString"
        assert len(primary["geometry"]["coordinates"]) == 4


def test_api_get_route_mangaluru_to_kundapura(client):
    """GET /api/v1/real-map/route computes reverse direction route."""
    params = {
        "origin_lat": 12.9141,
        "origin_lon": 74.8560,
        "destination_lat": 13.6268,
        "destination_lon": 74.6917,
        "origin_name": "Mangaluru",
        "destination_name": "Kundapura",
    }

    with patch.object(real_road_service, "_query_osrm", return_value=SAMPLE_OSRM_MANGALURU_KUNDAPURA):
        resp = client.get("/api/v1/real-map/route", params=params)
        assert resp.status_code == 200
        data = resp.json()

        assert data["origin"]["name"] == "Mangaluru"
        assert data["destination"]["name"] == "Kundapura"
        assert pytest.approx(data["primary_route"]["distance_km"], abs=0.1) == 91.52
        assert pytest.approx(data["primary_route"]["duration_minutes"], abs=0.2) == 82.1


def test_api_route_identical_coordinates_returns_400(client):
    """POST /api/v1/real-map/route returns HTTP 400 when origin and destination are identical."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 13.6268,
        "destination_lon": 74.6917,
    }
    resp = client.post("/api/v1/real-map/route", json=payload)
    assert resp.status_code == 400
    assert "too close or identical" in resp.json()["error"]["message"].lower()


def test_api_route_invalid_coordinates_range_returns_422(client):
    """POST /api/v1/real-map/route returns HTTP 422 on coordinates outside [-90, 90]."""
    payload = {
        "origin_lat": 99.0,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
    }
    resp = client.post("/api/v1/real-map/route", json=payload)
    assert resp.status_code == 422


def test_api_route_no_route_returns_404(client):
    """POST /api/v1/real-map/route returns HTTP 404 when provider cannot find a route."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
    }
    with patch.object(
        real_road_service,
        "_query_osrm",
        side_effect=NoRouteFoundError("No road route between selected coordinates"),
    ):
        resp = client.post("/api/v1/real-map/route", json=payload)
        assert resp.status_code == 404
        assert "no road route" in resp.json()["error"]["message"].lower()


def test_api_route_timeout_returns_504(client):
    """POST /api/v1/real-map/route returns HTTP 504 on provider timeout."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
    }
    with patch.object(
        real_road_service,
        "_query_osrm",
        side_effect=RoutingTimeoutError("Routing provider timed out after 10.0s."),
    ):
        resp = client.post("/api/v1/real-map/route", json=payload)
        assert resp.status_code == 504
        assert "timed out" in resp.json()["error"]["message"].lower()


def test_api_route_rate_limit_returns_429(client):
    """POST /api/v1/real-map/route returns HTTP 429 when rate limited."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
    }
    with patch.object(
        real_road_service,
        "_query_osrm",
        side_effect=RoutingRateLimitError("Rate limit exceeded"),
    ):
        resp = client.post("/api/v1/real-map/route", json=payload)
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["error"]["message"].lower()


def test_api_route_provider_error_returns_502(client):
    """POST /api/v1/real-map/route returns HTTP 502 on upstream connection error."""
    payload = {
        "origin_lat": 13.6268,
        "origin_lon": 74.6917,
        "destination_lat": 12.9141,
        "destination_lon": 74.8560,
    }
    with patch.object(
        real_road_service,
        "_query_osrm",
        side_effect=RoutingProviderError("Could not connect to road routing provider"),
    ):
        resp = client.post("/api/v1/real-map/route", json=payload)
        assert resp.status_code == 502
        assert "could not connect" in resp.json()["error"]["message"].lower()
