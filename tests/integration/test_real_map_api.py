"""Integration tests for the /api/v1/real-map/search geocoding endpoint."""

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
from backend.app.schemas.real_map import PlaceSearchResult
from backend.app.services.geocoding.service import (
    GeocodingProviderError,
    GeocodingRateLimitError,
    GeocodingTimeoutError,
    geocoding_service,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as tc:
        yield tc


def test_api_search_kundapura(client):
    """GET /api/v1/real-map/search?q=Kundapura returns verified cache results."""
    resp = client.get("/api/v1/real-map/search", params={"q": "Kundapura"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Kundapura"
    assert data["source"] == "verified_cache"
    assert data["count"] >= 1
    top = data["results"][0]
    assert top["name"] == "Kundapura"
    assert "Udupi" in top["display_name"]
    assert pytest.approx(top["lat"], abs=0.01) == 13.6268
    assert pytest.approx(top["lon"], abs=0.01) == 74.6917
    assert top["source"] == "verified_cache"


def test_api_search_mangaluru(client):
    """GET /api/v1/real-map/search?q=Mangaluru returns verified coordinates."""
    resp = client.get("/api/v1/real-map/search", params={"q": "Mangaluru"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "verified_cache"
    assert data["count"] >= 1
    top = data["results"][0]
    assert top["name"] == "Mangaluru"
    assert pytest.approx(top["lat"], abs=0.01) == 12.9141
    assert pytest.approx(top["lon"], abs=0.01) == 74.8560


def test_api_search_empty_and_whitespace_queries(client):
    """Empty or whitespace queries return HTTP 400 Bad Request."""
    resp_empty = client.get("/api/v1/real-map/search", params={"q": ""})
    assert resp_empty.status_code in (400, 422)

    resp_ws = client.get("/api/v1/real-map/search", params={"q": "   "})
    assert resp_ws.status_code == 400
    error_msg = resp_ws.json()["error"]["message"]
    assert "empty or whitespace" in error_msg.lower()


def test_api_search_short_query(client):
    """Queries under 2 characters return HTTP 400."""
    resp = client.get("/api/v1/real-map/search", params={"q": "k"})
    assert resp.status_code == 400


def test_api_search_unknown_location(client):
    """Unknown location with mocked empty OSM response returns count: 0."""
    with patch.object(geocoding_service, "_query_nominatim", return_value=[]):
        resp = client.get("/api/v1/real-map/search", params={"q": "AtlantisUnderwaterCity", "bypass_cache": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []
        assert data["source"] == "empty"


def test_api_search_timeout_error(client):
    """Provider timeout maps cleanly to HTTP 504 Gateway Timeout."""
    with patch.object(
        geocoding_service,
        "_query_nominatim",
        side_effect=GeocodingTimeoutError("Geocoding service timed out. Please try again."),
    ):
        resp = client.get("/api/v1/real-map/search", params={"q": "RemotePlace", "bypass_cache": "true"})
        assert resp.status_code == 504
        assert "timed out" in resp.json()["error"]["message"].lower()


def test_api_search_rate_limit_error(client):
    """Provider HTTP 429 maps cleanly to HTTP 429 Too Many Requests."""
    with patch.object(
        geocoding_service,
        "_query_nominatim",
        side_effect=GeocodingRateLimitError("Geocoding rate limit exceeded. Please try again in a moment."),
    ):
        resp = client.get("/api/v1/real-map/search", params={"q": "Anyplace", "bypass_cache": "true"})
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["error"]["message"].lower()


def test_api_search_provider_error(client):
    """Provider connection error maps cleanly to HTTP 502 Bad Gateway."""
    with patch.object(
        geocoding_service,
        "_query_nominatim",
        side_effect=GeocodingProviderError("Geocoding service unreachable: Connection refused"),
    ):
        resp = client.get("/api/v1/real-map/search", params={"q": "Anyplace", "bypass_cache": "true"})
        assert resp.status_code == 502
        assert "unreachable" in resp.json()["error"]["message"].lower()


def test_api_search_live_osm_mocked_results(client):
    """Valid OSM payload parses into typed PlaceSearchResult with source 'osm_nominatim'."""
    mock_place = PlaceSearchResult(
        id="osm_991234",
        display_name="Bengaluru, Karnataka, India",
        name="Bengaluru",
        lat=12.9716,
        lon=77.5946,
        source="osm_nominatim",
    )
    with patch.object(geocoding_service, "_query_nominatim", return_value=[mock_place]):
        resp = client.get("/api/v1/real-map/search", params={"q": "Bengaluru", "bypass_cache": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["source"] == "osm_nominatim"
        top = data["results"][0]
        assert top["id"] == "osm_991234"
        assert top["name"] == "Bengaluru"
        assert pytest.approx(top["lat"], abs=0.01) == 12.9716
        assert pytest.approx(top["lon"], abs=0.01) == 77.5946
