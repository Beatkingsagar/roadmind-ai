"""Journey Budget, Fuel Cost, and Toll Estimation Schemas.

Models structured payloads for:
1. Vehicle specifications and fuel types.
2. Fuel consumption and cost calculations (one-way and round-trip).
3. Toll estimations with strict zero-fabrication invariants.
4. Comprehensive journey budgets including full cost breakdowns and transparent assumptions.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


VehicleType = Literal["motorcycle", "car", "suv", "custom"]
FuelType = Literal["petrol", "diesel", "cng", "ev", "other"]
TollStatus = Literal["available", "unavailable", "disabled", "error"]


class TollPlazaInfo(BaseModel):
    """Information regarding a specific toll plaza encountered along a route."""

    plaza_name: str = Field(..., description="Official name or identifier of the toll plaza")
    road_name: Optional[str] = Field(None, description="Highway or corridor name (e.g. 'NH 66')")
    cost: float = Field(..., ge=0.0, description="Toll fee in specified currency")
    currency: str = Field(default="INR", description="Three-letter ISO currency code (default: INR)")
    payment_method: str = Field(
        default="fastag",
        description="Payment mode evaluated ('fastag' | 'cash' | 'electronic')",
    )
    is_confirmed: bool = Field(
        default=False,
        description="True if fee is an exact published statutory rate, False if estimated",
    )
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Plaza WGS84 latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Plaza WGS84 longitude")


class TollEstimate(BaseModel):
    """Structured toll cost estimate for a route corridor."""

    status: TollStatus = Field(
        default="unavailable",
        description="Toll data status: 'available' | 'unavailable' | 'disabled' | 'error'",
    )
    provider: str = Field(
        default="none",
        description="Verified toll provider identifier ('tollguru' | 'here' | 'none')",
    )
    total_toll: Optional[float] = Field(
        None,
        ge=0.0,
        description="Total toll amount in specified currency (None if toll data is unavailable)",
    )
    currency: str = Field(default="INR", description="Three-letter ISO currency code")
    plazas: List[TollPlazaInfo] = Field(
        default_factory=list,
        description="List of detected toll plazas (empty if unavailable or no plazas on route)",
    )
    is_confirmed: bool = Field(
        default=False,
        description="True if toll amount represents verified tariff data, False if estimated or unavailable",
    )
    is_estimated: bool = Field(
        default=False,
        description="True if toll is derived from heuristics/estimates rather than confirmed published rates",
    )
    source: str = Field(
        default="none",
        description="Source of toll data or explanation (e.g. 'TollGuru India API' or 'No verified toll provider configured')",
    )
    message: str = Field(
        default="Toll estimate unavailable",
        description="Human-readable explanation of toll availability and pricing status",
    )


class FuelCostEstimate(BaseModel):
    """Granular fuel consumption and financial cost calculation."""

    fuel_required_units: float = Field(
        ...,
        ge=0.0,
        description="Estimated fuel quantity required (litres for petrol/diesel, kg for CNG, kWh for EV)",
    )
    fuel_unit: str = Field(
        default="L",
        description="Unit of fuel measurement ('L', 'kg', 'kWh', 'unit')",
    )
    fuel_price_per_unit: float = Field(
        ...,
        ge=0.0,
        description="Fuel price per unit in currency (e.g. ₹ per litre)",
    )
    fuel_efficiency_km_per_unit: float = Field(
        ...,
        gt=0.0,
        description="Vehicle fuel efficiency in km per unit",
    )
    one_way_fuel_cost: float = Field(
        ...,
        ge=0.0,
        description="Estimated fuel cost for a single one-way trip",
    )
    return_trip_fuel_cost: float = Field(
        ...,
        ge=0.0,
        description="Estimated fuel cost for a two-way return trip (2x one-way distance)",
    )
    active_fuel_cost: float = Field(
        ...,
        ge=0.0,
        description="Active fuel cost based on whether round-trip is selected",
    )
    is_round_trip: bool = Field(
        default=False,
        description="Whether this active calculation represents a round-trip journey",
    )


class JourneyBudgetRequest(BaseModel):
    """Client request to calculate fuel costs and journey budget."""

    distance_km: float = Field(
        ...,
        gt=0.0,
        description="Actual road distance in kilometres returned by routing provider",
    )
    vehicle_type: VehicleType = Field(
        default="car",
        description="Vehicle classification: 'motorcycle' | 'car' | 'suv' | 'custom'",
    )
    custom_vehicle_name: Optional[str] = Field(
        None,
        description="User-defined vehicle label when vehicle_type is 'custom'",
    )
    fuel_type: FuelType = Field(
        default="petrol",
        description="Fuel type: 'petrol' | 'diesel' | 'cng' | 'ev' | 'other'",
    )
    fuel_efficiency_km_per_unit: float = Field(
        ...,
        gt=0.0,
        description="Vehicle fuel efficiency in km/litre (or km/kg or km/kWh)",
    )
    fuel_price_per_unit: float = Field(
        ...,
        ge=0.0,
        description="Fuel price per litre or unit entered by user",
    )
    is_round_trip: bool = Field(
        default=False,
        description="If True, calculate total costs for a round-trip journey (2x distance)",
    )
    encoded_polyline: Optional[str] = Field(
        None,
        description="Optional encoded route polyline string for toll lookup",
    )
    route_geometry: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional GeoJSON LineString geometry for toll corridor matching",
    )
    origin_name: Optional[str] = Field(None, description="Optional origin place name")
    destination_name: Optional[str] = Field(None, description="Optional destination place name")

    @field_validator("distance_km")
    @classmethod
    def validate_distance(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or v <= 0.0:
            raise ValueError("Distance must be a valid positive number greater than 0 km.")
        return round(v, 3)

    @field_validator("fuel_efficiency_km_per_unit")
    @classmethod
    def validate_efficiency(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or v <= 0.0:
            raise ValueError("Fuel efficiency must be a valid positive number greater than 0.")
        if v > 200.0:
            raise ValueError("Fuel efficiency exceeds realistic limits (max 200 km/unit).")
        return round(v, 2)

    @field_validator("fuel_price_per_unit")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or v < 0.0:
            raise ValueError("Fuel price must be a valid non-negative number.")
        if v > 10000.0:
            raise ValueError("Fuel price exceeds realistic limits.")
        return round(v, 2)


class JourneyBudgetResponse(BaseModel):
    """Complete journey cost breakdown and budget report."""

    distance_km: float = Field(..., ge=0.0, description="One-way route road distance in km")
    effective_distance_km: float = Field(
        ..., ge=0.0, description="Total distance accounted for in budget (1x or 2x distance)"
    )
    is_round_trip: bool = Field(..., description="Whether this budget includes return-trip travel")
    vehicle_type: str = Field(..., description="Vehicle type classification")
    vehicle_label: str = Field(..., description="Human-readable vehicle display name")
    fuel_type: str = Field(..., description="Fuel type identifier")
    fuel_cost: FuelCostEstimate = Field(..., description="Detailed fuel consumption and costs")
    toll: TollEstimate = Field(..., description="Toll estimation status and breakdown")
    estimated_total_cost: float = Field(
        ...,
        ge=0.0,
        description="Total estimated journey budget (fuel + tolls if available)",
    )
    total_includes_toll: bool = Field(
        ...,
        description="True if confirmed or estimated toll amounts are included in total_cost",
    )
    currency: str = Field(default="INR", description="Currency symbol / code")
    assumptions: List[str] = Field(
        default_factory=list,
        description="Explicit calculation formulas, parameters, and limitations used",
    )


class TollEstimateRequest(BaseModel):
    """Request payload for standalone toll estimation."""

    route_distance_km: Optional[float] = Field(None, ge=0.0, description="Total route distance in km")
    encoded_polyline: Optional[str] = Field(None, description="Encoded polyline of the route")
    route_geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry of the route")
    vehicle_type: VehicleType = Field(default="car", description="Vehicle type classification")
    is_round_trip: bool = Field(default=False, description="Whether route is round-trip")


class TollStatusResponse(BaseModel):
    """System-level toll provider audit and operational status."""

    active_provider: str = Field(..., description="Active toll provider identifier ('tollguru' | 'here' | 'none')")
    is_configured: bool = Field(..., description="True if provider credentials are set in configuration")
    is_available: bool = Field(..., description="True if provider service is currently operational")
    message: str = Field(..., description="Status description and operational explanation")
    supported_regions: List[str] = Field(
        default_factory=list,
        description="List of regional road networks supported (e.g. ['Karnataka National Highways', 'NH 66'])",
    )
