"""Journey Budget and Fuel Cost Service.

Calculates real-world journey budgets combining:
1. Route distance from verified road network routing provider.
2. Fuel consumption based on vehicle efficiency (km/litre or equivalent).
3. Financial costs for one-way and round-trip journeys.
4. Toll estimations from dedicated toll providers with zero-fabrication guarantees.
5. Explicit, transparent assumptions and parameters used in the calculation.
"""

from __future__ import annotations

import logging
from typing import List
from backend.app.schemas.journey_budget import (
    FuelCostEstimate,
    JourneyBudgetRequest,
    JourneyBudgetResponse,
    TollEstimate,
)
from backend.app.services.toll import toll_service

logger = logging.getLogger(__name__)


VEHICLE_LABELS = {
    "motorcycle": "Motorcycle / Two-Wheeler",
    "car": "Standard Car / Hatchback / Sedan",
    "suv": "SUV / MUV / Compact Truck",
    "custom": "Custom Vehicle",
}

FUEL_UNITS = {
    "petrol": "L",
    "diesel": "L",
    "cng": "kg",
    "ev": "kWh",
    "other": "unit",
}


class JourneyBudgetService:
    """Service for computing journey budgets and fuel expenses."""

    def __init__(self, toll_svc=None) -> None:
        self.toll_svc = toll_svc or toll_service

    def calculate_budget(self, request: JourneyBudgetRequest) -> JourneyBudgetResponse:
        """Compute comprehensive journey budget from request parameters.

        Formulas:
        - Fuel required = route distance / fuel efficiency
        - Fuel cost = fuel required × fuel price per unit
        - Round-trip cost = 2 × one-way cost
        - Total journey cost = active fuel cost + (toll estimate if available else 0.0)
        """
        distance_km = request.distance_km
        efficiency = request.fuel_efficiency_km_per_unit
        price = request.fuel_price_per_unit
        is_round_trip = request.is_round_trip

        unit = FUEL_UNITS.get(request.fuel_type, "L")
        vehicle_label = (
            request.custom_vehicle_name
            if (request.vehicle_type == "custom" and request.custom_vehicle_name)
            else VEHICLE_LABELS.get(request.vehicle_type, "Standard Vehicle")
        )

        # 1. Distance Metrics
        effective_distance_km = round(distance_km * 2.0 if is_round_trip else distance_km, 2)

        # 2. Fuel Consumption & Cost Math
        one_way_fuel_required = distance_km / efficiency
        one_way_cost = round(one_way_fuel_required * price, 2)

        return_trip_fuel_required = (distance_km * 2.0) / efficiency
        return_trip_cost = round(return_trip_fuel_required * price, 2)

        active_fuel_required = round(
            return_trip_fuel_required if is_round_trip else one_way_fuel_required, 2
        )
        active_fuel_cost = return_trip_cost if is_round_trip else one_way_cost

        fuel_estimate = FuelCostEstimate(
            fuel_required_units=active_fuel_required,
            fuel_unit=unit,
            fuel_price_per_unit=price,
            fuel_efficiency_km_per_unit=efficiency,
            one_way_fuel_cost=one_way_cost,
            return_trip_fuel_cost=return_trip_cost,
            active_fuel_cost=active_fuel_cost,
            is_round_trip=is_round_trip,
        )

        # 3. Toll Estimation (Zero Fabrication Guarantee)
        toll_estimate: TollEstimate
        try:
            toll_estimate = self.toll_svc.estimate_toll(
                encoded_polyline=request.encoded_polyline,
                route_geometry=request.route_geometry,
                route_distance_km=distance_km,
                vehicle_type=request.vehicle_type,
                is_round_trip=is_round_trip,
            )
        except Exception as exc:
            logger.warning("Error fetching toll estimate: %s", exc)
            toll_estimate = TollEstimate(
                status="unavailable",
                provider="none",
                total_toll=None,
                currency="INR",
                plazas=[],
                is_confirmed=False,
                is_estimated=False,
                source="none",
                message="Toll estimate unavailable: Internal toll evaluation error.",
            )

        # 4. Total Budget Assembly
        has_toll = toll_estimate.status == "available" and toll_estimate.total_toll is not None
        toll_cost = toll_estimate.total_toll if has_toll and toll_estimate.total_toll is not None else 0.0
        total_cost = round(active_fuel_cost + toll_cost, 2)

        # 5. Build Transparent Assumptions Audit Trail
        assumptions: List[str] = [
            f"Route distance: {distance_km:.2f} km as calculated by road network routing engine (OSRM).",
        ]

        if is_round_trip:
            assumptions.append(
                f"Trip type: Round-trip (2× one-way distance = {effective_distance_km:.2f} km)."
            )
        else:
            assumptions.append("Trip type: One-way journey.")

        assumptions.append(
            f"Vehicle: {vehicle_label} with efficiency {efficiency:.2f} km/{unit}."
        )
        assumptions.append(
            f"Fuel: {request.fuel_type.capitalize()} at ₹{price:.2f} per {unit}."
        )
        assumptions.append(
            f"Formula: Fuel required ({active_fuel_required:.2f} {unit}) = "
            f"Distance ({effective_distance_km:.2f} km) ÷ Efficiency ({efficiency:.2f} km/{unit})."
        )
        assumptions.append(
            f"Formula: Fuel cost (₹{active_fuel_cost:.2f}) = "
            f"Fuel required ({active_fuel_required:.2f} {unit}) × Price per unit (₹{price:.2f})."
        )

        if has_toll:
            confirm_label = "Confirmed rate" if toll_estimate.is_confirmed else "Estimated rate"
            assumptions.append(
                f"Tolls included: ₹{toll_cost:.2f} ({confirm_label}) across {len(toll_estimate.plazas)} plaza(s) via {toll_estimate.source}."
            )
        else:
            assumptions.append(
                "Tolls excluded: Toll estimate unavailable (no verified toll provider configured). "
                "Total budget reflects fuel consumption only."
            )

        assumptions.append(
            "Assumption: Real-world highway fuel consumption assumes steady driving; "
            "severe traffic delays or terrain may affect actual mileage."
        )

        return JourneyBudgetResponse(
            distance_km=round(distance_km, 2),
            effective_distance_km=effective_distance_km,
            is_round_trip=is_round_trip,
            vehicle_type=request.vehicle_type,
            vehicle_label=vehicle_label,
            fuel_type=request.fuel_type,
            fuel_cost=fuel_estimate,
            toll=toll_estimate,
            estimated_total_cost=total_cost,
            total_includes_toll=has_toll,
            currency="INR",
            assumptions=assumptions,
        )


# Global singleton instance
journey_budget_service = JourneyBudgetService()
