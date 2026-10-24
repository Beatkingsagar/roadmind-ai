"""Unit tests for Fuel Cost Calculator, Toll Estimation, and Journey Budget Service."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.journey_budget import (
    FuelCostEstimate,
    JourneyBudgetRequest,
    JourneyBudgetResponse,
    TollEstimate,
    TollPlazaInfo,
)
from backend.app.services.budget.budget_service import JourneyBudgetService
from backend.app.services.toll.toll_service import TollService


@pytest.fixture
def empty_toll_service():
    """Toll service instance with no API key configured."""
    return TollService(provider="none", api_key=None)


@pytest.fixture
def budget_service(empty_toll_service):
    """Budget service configured with empty toll service."""
    return JourneyBudgetService(toll_svc=empty_toll_service)


def test_fuel_cost_calculation_one_way(budget_service):
    """Test standard fuel cost calculation for one-way journey."""
    # Kundapura to Mangaluru: 91.9 km, Car @ 15.0 km/L, Petrol @ ₹103.50/L
    req = JourneyBudgetRequest(
        distance_km=91.9,
        vehicle_type="car",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=15.0,
        fuel_price_per_unit=103.50,
        is_round_trip=False,
    )
    res = budget_service.calculate_budget(req)

    assert res.distance_km == 91.9
    assert res.effective_distance_km == 91.9
    assert res.is_round_trip is False

    # Formula checks:
    # 91.9 / 15.0 = 6.12666... -> 6.13 L
    expected_fuel = round(91.9 / 15.0, 2)
    assert res.fuel_cost.fuel_required_units == expected_fuel
    assert res.fuel_cost.fuel_unit == "L"

    # 6.12666... * 103.50 = 634.11
    expected_one_way_cost = round((91.9 / 15.0) * 103.50, 2)
    assert res.fuel_cost.one_way_fuel_cost == expected_one_way_cost
    assert res.fuel_cost.active_fuel_cost == expected_one_way_cost
    assert res.estimated_total_cost == expected_one_way_cost
    assert res.total_includes_toll is False


def test_round_trip_estimate(budget_service):
    """Test round-trip journey calculation doubles distance and cost."""
    req = JourneyBudgetRequest(
        distance_km=91.9,
        vehicle_type="car",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=15.0,
        fuel_price_per_unit=103.50,
        is_round_trip=True,
    )
    res = budget_service.calculate_budget(req)

    assert res.distance_km == 91.9
    assert res.effective_distance_km == 183.8
    assert res.is_round_trip is True

    one_way_cost = round((91.9 / 15.0) * 103.50, 2)
    expected_round_trip_cost = round(((91.9 * 2.0) / 15.0) * 103.50, 2)

    assert res.fuel_cost.return_trip_fuel_cost == expected_round_trip_cost
    assert res.fuel_cost.active_fuel_cost == expected_round_trip_cost
    assert res.estimated_total_cost == expected_round_trip_cost
    assert math.isclose(res.fuel_cost.active_fuel_cost, one_way_cost * 2, abs_tol=0.05)


def test_different_vehicle_efficiencies(budget_service):
    """Test fuel cost calculations across motorcycle, car, SUV, and custom vehicle."""
    # 1. Motorcycle (high efficiency: 45 km/L)
    req_moto = JourneyBudgetRequest(
        distance_km=90.0,
        vehicle_type="motorcycle",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=45.0,
        fuel_price_per_unit=103.50,
    )
    res_moto = budget_service.calculate_budget(req_moto)
    assert res_moto.fuel_cost.fuel_required_units == 2.0
    assert res_moto.fuel_cost.active_fuel_cost == 207.0

    # 2. SUV (lower efficiency: 12 km/L)
    req_suv = JourneyBudgetRequest(
        distance_km=90.0,
        vehicle_type="suv",
        fuel_type="diesel",
        fuel_efficiency_km_per_unit=12.0,
        fuel_price_per_unit=89.50,
    )
    res_suv = budget_service.calculate_budget(req_suv)
    assert res_suv.fuel_cost.fuel_required_units == 7.5
    assert res_suv.fuel_cost.active_fuel_cost == 671.25

    # 3. Custom vehicle
    req_custom = JourneyBudgetRequest(
        distance_km=90.0,
        vehicle_type="custom",
        custom_vehicle_name="Vintage Scooter",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=30.0,
        fuel_price_per_unit=100.0,
    )
    res_custom = budget_service.calculate_budget(req_custom)
    assert res_custom.vehicle_label == "Vintage Scooter"
    assert res_custom.fuel_cost.fuel_required_units == 3.0
    assert res_custom.fuel_cost.active_fuel_cost == 300.0


def test_supported_fuel_types_and_units(budget_service):
    """Test CNG and EV units and calculations."""
    # CNG in kg
    req_cng = JourneyBudgetRequest(
        distance_km=100.0,
        vehicle_type="car",
        fuel_type="cng",
        fuel_efficiency_km_per_unit=25.0,
        fuel_price_per_unit=85.0,
    )
    res_cng = budget_service.calculate_budget(req_cng)
    assert res_cng.fuel_cost.fuel_unit == "kg"
    assert res_cng.fuel_cost.fuel_required_units == 4.0
    assert res_cng.fuel_cost.active_fuel_cost == 340.0

    # EV in kWh
    req_ev = JourneyBudgetRequest(
        distance_km=100.0,
        vehicle_type="car",
        fuel_type="ev",
        fuel_efficiency_km_per_unit=7.0,
        fuel_price_per_unit=8.50,
    )
    res_ev = budget_service.calculate_budget(req_ev)
    assert res_ev.fuel_cost.fuel_unit == "kWh"
    assert res_ev.fuel_cost.fuel_required_units == round(100.0 / 7.0, 2)


def test_invalid_and_zero_inputs_rejected():
    """Verify robust validation rejects zero or negative efficiency, negative prices, and bad distance."""
    # Zero efficiency must fail
    with pytest.raises(ValueError):
        JourneyBudgetRequest(
            distance_km=91.9,
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=0.0,
            fuel_price_per_unit=103.50,
        )

    # Negative efficiency must fail
    with pytest.raises(ValueError):
        JourneyBudgetRequest(
            distance_km=91.9,
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=-15.0,
            fuel_price_per_unit=103.50,
        )

    # Negative price must fail
    with pytest.raises(ValueError):
        JourneyBudgetRequest(
            distance_km=91.9,
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=15.0,
            fuel_price_per_unit=-10.0,
        )

    # Zero distance must fail
    with pytest.raises(ValueError):
        JourneyBudgetRequest(
            distance_km=0.0,
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=15.0,
            fuel_price_per_unit=103.50,
        )

    # NaN must fail
    with pytest.raises(ValueError):
        JourneyBudgetRequest(
            distance_km=float("nan"),
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=15.0,
            fuel_price_per_unit=103.50,
        )


def test_toll_data_unavailable_zero_fabrication_invariant(budget_service):
    """Strict verification: When toll credentials are not configured,
    system NEVER invents toll plazas or fictional rupee prices."""
    req = JourneyBudgetRequest(
        distance_km=91.9,
        vehicle_type="car",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=15.0,
        fuel_price_per_unit=103.50,
        route_geometry={"type": "LineString", "coordinates": [[74.69, 13.62], [74.85, 12.91]]},
    )
    res = budget_service.calculate_budget(req)

    assert res.toll.status == "unavailable"
    assert res.toll.total_toll is None
    assert len(res.toll.plazas) == 0
    assert "Toll estimate unavailable" in res.toll.message
    assert res.total_includes_toll is False
    # Total equals fuel cost exactly
    assert res.estimated_total_cost == res.fuel_cost.active_fuel_cost

    # Audit assumptions mention exclusion
    assumptions_text = " ".join(res.assumptions)
    assert "Tolls excluded" in assumptions_text


def test_toll_service_status_audit():
    """Verify toll service status returns transparent provider info without leaks."""
    unconfigured = TollService(provider="auto", api_key=None)
    status_unconfigured = unconfigured.get_status()
    assert status_unconfigured.is_configured is False
    assert status_unconfigured.is_available is False
    assert "No verified toll provider" in status_unconfigured.message
    assert "Karnataka National Highways" in status_unconfigured.supported_regions[0]

    configured = TollService(provider="tollguru", api_key="secret_test_key_123")
    status_configured = configured.get_status()
    assert status_configured.is_configured is True
    assert status_configured.is_available is True
    assert status_configured.active_provider == "tollguru"


def test_mocked_toll_provider_success():
    """Verify parsing when verified toll provider returns authentic tariff data."""
    mock_toll_svc = TollService(provider="tollguru", api_key="test_key")

    mock_response_data = {
        "routes": [
            {
                "costs": {"tag": 125.0, "cash": 250.0},
                "tolls": [
                    {
                        "name": "Hejamadi Toll Plaza",
                        "road": "NH 66",
                        "tagCost": 60.0,
                        "location": {"lat": 13.142, "lng": 74.781},
                    },
                    {
                        "name": "Sasthan Toll Plaza",
                        "road": "NH 66",
                        "tagCost": 65.0,
                        "location": {"lat": 13.518, "lng": 74.712},
                    },
                ],
            }
        ]
    }

    with patch.object(mock_toll_svc, "_query_tollguru") as mock_query:
        mock_query.return_value = TollEstimate(
            status="available",
            provider="tollguru",
            total_toll=125.0,
            currency="INR",
            plazas=[
                TollPlazaInfo(plaza_name="Hejamadi Toll Plaza", road_name="NH 66", cost=60.0, is_confirmed=True),
                TollPlazaInfo(plaza_name="Sasthan Toll Plaza", road_name="NH 66", cost=65.0, is_confirmed=True),
            ],
            is_confirmed=True,
            is_estimated=False,
            source="TollGuru India API",
            message="Estimated One-way tolls: ₹125.00 across 2 plaza(s) via TollGuru.",
        )

        b_svc = JourneyBudgetService(toll_svc=mock_toll_svc)
        req = JourneyBudgetRequest(
            distance_km=91.9,
            vehicle_type="car",
            fuel_type="petrol",
            fuel_efficiency_km_per_unit=15.0,
            fuel_price_per_unit=100.0,
            is_round_trip=False,
            encoded_polyline="dummy_polyline_str",
        )
        res = b_svc.calculate_budget(req)

        assert res.toll.status == "available"
        assert res.toll.total_toll == 125.0
        assert res.toll.is_confirmed is True
        assert len(res.toll.plazas) == 2
        assert res.total_includes_toll is True
        # Total cost = 91.9/15.0 * 100 = 612.67 + 125.0 = 737.67
        expected_fuel = round((91.9 / 15.0) * 100.0, 2)
        assert res.estimated_total_cost == round(expected_fuel + 125.0, 2)


def test_toll_provider_timeout_graceful_degradation():
    """Verify network timeout on toll provider returns error status without failing calculation."""
    mock_toll_svc = TollService(provider="tollguru", api_key="test_key")

    with patch.object(mock_toll_svc, "_query_tollguru") as mock_query:
        from backend.app.services.toll.toll_service import TollTimeoutError
        mock_query.side_effect = TollTimeoutError("Connection timed out")

        estimate = mock_toll_svc.estimate_toll(encoded_polyline="test_poly")
        assert estimate.status == "error"
        assert "timed out" in estimate.message
        assert estimate.total_toll is None


def test_route_changes_update_estimated_costs(budget_service):
    """Verify switching between primary route distance and alternative route distance updates cost."""
    primary_dist = 91.9   # NH 66
    alternative_dist = 99.4 # via State Highway

    req_primary = JourneyBudgetRequest(
        distance_km=primary_dist,
        vehicle_type="car",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=15.0,
        fuel_price_per_unit=100.0,
    )
    res_primary = budget_service.calculate_budget(req_primary)

    req_alt = JourneyBudgetRequest(
        distance_km=alternative_dist,
        vehicle_type="car",
        fuel_type="petrol",
        fuel_efficiency_km_per_unit=15.0,
        fuel_price_per_unit=100.0,
    )
    res_alt = budget_service.calculate_budget(req_alt)

    assert res_primary.fuel_cost.active_fuel_cost < res_alt.fuel_cost.active_fuel_cost
    assert res_alt.fuel_cost.active_fuel_cost == round((99.4 / 15.0) * 100.0, 2)
