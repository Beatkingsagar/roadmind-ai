"""Integration tests for Real Map Journey Budget and Toll REST API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_api_budget_calculation_success():
    """Verify POST /api/v1/real-map/budget returns accurate calculation."""
    payload = {
        "distance_km": 91.9,
        "vehicle_type": "car",
        "fuel_type": "petrol",
        "fuel_efficiency_km_per_unit": 15.0,
        "fuel_price_per_unit": 103.50,
        "is_round_trip": False,
    }
    resp = client.post("/api/v1/real-map/budget", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["distance_km"] == 91.9
    assert data["effective_distance_km"] == 91.9
    assert data["is_round_trip"] is False
    assert data["vehicle_type"] == "car"
    assert data["fuel_cost"]["fuel_unit"] == "L"
    assert data["fuel_cost"]["active_fuel_cost"] == 634.11
    assert data["toll"]["status"] in ("available", "unavailable")
    assert len(data["assumptions"]) > 0


def test_api_budget_round_trip_calculation():
    """Verify round-trip budget request calculates return journey."""
    payload = {
        "distance_km": 91.9,
        "vehicle_type": "motorcycle",
        "fuel_type": "petrol",
        "fuel_efficiency_km_per_unit": 45.0,
        "fuel_price_per_unit": 100.0,
        "is_round_trip": True,
    }
    resp = client.post("/api/v1/real-map/budget", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_round_trip"] is True
    assert data["effective_distance_km"] == 183.8
    # 183.8 / 45.0 * 100 = ~408.44
    assert data["fuel_cost"]["active_fuel_cost"] == 408.44
    assert data["fuel_cost"]["return_trip_fuel_cost"] == 408.44


def test_api_budget_invalid_inputs_return_422():
    """Verify invalid parameters (zero or negative efficiency/price) return 422."""
    # Zero efficiency
    resp_zero_eff = client.post(
        "/api/v1/real-map/budget",
        json={
            "distance_km": 91.9,
            "vehicle_type": "car",
            "fuel_type": "petrol",
            "fuel_efficiency_km_per_unit": 0.0,
            "fuel_price_per_unit": 100.0,
        },
    )
    assert resp_zero_eff.status_code == 422

    # Negative price
    resp_neg_price = client.post(
        "/api/v1/real-map/budget",
        json={
            "distance_km": 91.9,
            "vehicle_type": "car",
            "fuel_type": "petrol",
            "fuel_efficiency_km_per_unit": 15.0,
            "fuel_price_per_unit": -50.0,
        },
    )
    assert resp_neg_price.status_code == 422

    # Zero distance
    resp_zero_dist = client.post(
        "/api/v1/real-map/budget",
        json={
            "distance_km": 0.0,
            "vehicle_type": "car",
            "fuel_type": "petrol",
            "fuel_efficiency_km_per_unit": 15.0,
            "fuel_price_per_unit": 100.0,
        },
    )
    assert resp_zero_dist.status_code == 422


def test_api_toll_status_endpoint():
    """Verify GET /api/v1/real-map/toll/status returns provider status."""
    resp = client.get("/api/v1/real-map/toll/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "active_provider" in data
    assert "is_configured" in data
    assert "supported_regions" in data
    assert any("Karnataka" in region for region in data["supported_regions"])


def test_api_toll_estimation_unconfigured_returns_unavailable():
    """Verify POST /api/v1/real-map/toll returns unavailable when provider not configured."""
    payload = {
        "route_distance_km": 91.9,
        "vehicle_type": "car",
    }
    resp = client.post("/api/v1/real-map/toll", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Must NOT invent fictional toll amounts or fake plazas
    if not data.get("is_confirmed"):
        assert data["status"] in ("unavailable", "disabled", "error")
        assert data["total_toll"] is None or data["total_toll"] == 0.0
        assert data["plazas"] == []


def test_separation_of_real_world_and_synthetic_modes():
    """Ensure synthetic Sector 7 demo endpoints remain clean and distinct from real-world budget."""
    # 1. Synthetic network endpoint verification
    synth_net_resp = client.get("/api/v1/network")
    assert synth_net_resp.status_code == 200
    synth_net_data = synth_net_resp.json()

    assert synth_net_data["data_mode"] == "synthetic"
    assert "fuel_cost" not in synth_net_data
    assert "toll" not in synth_net_data

    # 2. Real-world route and budget endpoints remain strictly segregated from synthetic simulation schemas
    budget_payload = {
        "distance_km": 91.9,
        "vehicle_type": "car",
        "fuel_type": "petrol",
        "fuel_efficiency_km_per_unit": 15.0,
        "fuel_price_per_unit": 103.50,
    }
    budget_resp = client.post("/api/v1/real-map/budget", json=budget_payload)
    assert budget_resp.status_code == 200
    b_data = budget_resp.json()

    # Budget response has currency and fuel cost, not synthetic scenario overrides
    assert "fuel_cost" in b_data
    assert "toll" in b_data
    assert "baseline_route" not in b_data
    assert "recommendation" not in b_data
    assert b_data["currency"] == "INR"

