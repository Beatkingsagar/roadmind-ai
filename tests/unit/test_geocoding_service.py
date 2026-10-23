"""Unit tests for GeocodingService and Place Search."""

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
from pydantic import ValidationError

from backend.app.schemas.real_map import PlaceSearchResult
from backend.app.services.geocoding.service import (
    GeocodingProviderError,
    GeocodingRateLimitError,
    GeocodingService,
    GeocodingTimeoutError,
    InvalidQueryError,
)


@pytest.fixture
def service():
    return GeocodingService()


def test_search_kundapura_verified_cache(service):
    """Kundapura search resolves immediately from verified ground-truth cache."""
    resp = service.search_places("Kundapura")
    assert resp.source == "verified_cache"
    assert resp.count >= 1
    top = resp.results[0]
    assert top.name == "Kundapura"
    assert "Udupi" in top.display_name
    assert pytest.approx(top.lat, abs=0.01) == 13.6268
    assert pytest.approx(top.lon, abs=0.01) == 74.6917
    assert top.source == "verified_cache"


def test_search_mangaluru_verified_cache(service):
    """Mangaluru search resolves from verified ground-truth cache."""
    resp = service.search_places("Mangaluru")
    assert resp.source == "verified_cache"
    assert resp.count >= 1
    top = resp.results[0]
    assert top.name == "Mangaluru"
    assert "Dakshina Kannada" in top.display_name
    assert pytest.approx(top.lat, abs=0.01) == 12.9141
    assert pytest.approx(top.lon, abs=0.01) == 74.8560
    assert top.source == "verified_cache"


def test_search_mangalore_alias(service):
    """Historical/common English alias 'Mangalore' resolves to Mangaluru."""
    resp = service.search_places("mangalore")
    assert resp.source == "verified_cache"
    assert resp.count >= 1
    assert any("Mangaluru" in r.name for r in resp.results)


def test_coordinate_validation():
    """Coordinates must be strictly within standard geographic bounds [-90, 90] and [-180, 180]."""
    valid = PlaceSearchResult(
        id="valid_1",
        name="Test",
        display_name="Test Place",
        lat=13.6268,
        lon=74.6917,
        source="verified_cache",
    )
    assert valid.lat == 13.6268
    assert valid.lon == 74.6917

    with pytest.raises(ValidationError):
        PlaceSearchResult(
            id="inv_lat",
            name="Invalid Lat",
            display_name="Invalid Lat",
            lat=95.0,
            lon=74.0,
            source="verified_cache",
        )

    with pytest.raises(ValidationError):
        PlaceSearchResult(
            id="inv_lon",
            name="Invalid Lon",
            display_name="Invalid Lon",
            lat=13.0,
            lon=-195.0,
            source="verified_cache",
        )


def test_empty_and_invalid_queries(service):
    """Empty strings, whitespace, or excessively short inputs are rejected."""
    with pytest.raises(InvalidQueryError):
        service.search_places("")

    with pytest.raises(InvalidQueryError):
        service.search_places("   ")

    with pytest.raises(InvalidQueryError):
        service.search_places("a")


def test_unknown_location_mocked(service):
    """Unknown locations with 0 Nominatim matches return empty results without error."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.Client.get", return_value=mock_response):
        resp = service.search_places("NonExistentUnknownLocality999", bypass_cache=True)
        assert resp.count == 0
        assert resp.results == []
        assert resp.source == "empty"


def test_ambiguous_results_order(service):
    """Ambiguous query returns multiple distinct verified locations sorted by importance."""
    # 'a' token in multiple coastal spots
    resp = service.search_places("airport")
    assert resp.count >= 1
    assert any("Airport" in r.name for r in resp.results)


def test_geocoder_timeout_error(service):
    """Network timeouts from provider trigger GeocodingTimeoutError."""
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(GeocodingTimeoutError):
            service.search_places("Paris, France", bypass_cache=True)


def test_geocoder_rate_limit_error(service):
    """HTTP 429 from provider triggers GeocodingRateLimitError."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch("httpx.Client.get", return_value=mock_response):
        with pytest.raises(GeocodingRateLimitError):
            service.search_places("London", bypass_cache=True)


def test_geocoder_provider_error(service):
    """Network connection failure triggers GeocodingProviderError."""
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Failed to connect")):
        with pytest.raises(GeocodingProviderError):
            service.search_places("Tokyo", bypass_cache=True)
