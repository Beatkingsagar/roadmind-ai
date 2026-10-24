import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Fuel,
  Car,
  Bike,
  Truck,
  Sliders,
  Info,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';


import {
  VEHICLE_PRESETS,
  FUEL_PRESETS,
  type VehiclePreset,
  type FuelPreset,
} from '../../utils/constants';
import {
  formatCurrency,
  computeClientJourneyBudget,
} from '../../utils/formatters';
import { api } from '../../api/client';
import type { TollEstimate } from '../../api/types';

interface JourneyBudgetCalculatorProps {
  /** Distance in kilometres returned by road routing provider */
  distanceKm: number;
  /** Route summary label (e.g. 'NH 66') */
  routeSummary?: string;
  /** Optional route polyline or geometry for toll lookup */
  encodedPolyline?: string;
  routeGeometry?: Record<string, unknown>;
  originName?: string;
  destinationName?: string;
}

export const JourneyBudgetCalculator: React.FC<JourneyBudgetCalculatorProps> = ({
  distanceKm,
  routeSummary,
  encodedPolyline,
  routeGeometry,
  originName,
  destinationName,
}) => {
  // Vehicle Selection
  const [selectedVehicleType, setSelectedVehicleType] = useState<VehiclePreset['id']>('car');
  const [customVehicleName, setCustomVehicleName] = useState<string>('My Vehicle');

  // Fuel Selection
  const [selectedFuelType, setSelectedFuelType] = useState<FuelPreset['id']>('petrol');

  // User-Editable Numeric Inputs
  const [efficiencyInput, setEfficiencyInput] = useState<string>('15.0');
  const [priceInput, setPriceInput] = useState<string>('103.50');

  // Trip Mode
  const [isRoundTrip, setIsRoundTrip] = useState<boolean>(false);

  // Toll Estimate State (Queried from Backend Service)
  const [tollEstimate, setTollEstimate] = useState<TollEstimate | null>(null);
  const [isLoadingToll, setIsLoadingToll] = useState<boolean>(false);

  // Assumptions toggle
  const [showAssumptions, setShowAssumptions] = useState<boolean>(false);

  // Find active presets
  const activeVehiclePreset = useMemo(
    () => VEHICLE_PRESETS.find((v) => v.id === selectedVehicleType) || VEHICLE_PRESETS[1],
    [selectedVehicleType]
  );

  const activeFuelPreset = useMemo(
    () => FUEL_PRESETS.find((f) => f.id === selectedFuelType) || FUEL_PRESETS[0],
    [selectedFuelType]
  );

  // When vehicle type changes, set sensible default efficiency if not customized
  const handleSelectVehicle = (preset: VehiclePreset) => {
    setSelectedVehicleType(preset.id);
    setEfficiencyInput(preset.defaultEfficiency.toFixed(1));
  };

  // When fuel type changes, set regional retail benchmark price
  const handleSelectFuel = (preset: FuelPreset) => {
    setSelectedFuelType(preset.id);
    setPriceInput(preset.defaultPrice.toFixed(2));
  };

  // Parse numeric values with safety
  const efficiencyNum = parseFloat(efficiencyInput);
  const priceNum = parseFloat(priceInput);

  // Fetch Toll Estimate from Backend when route changes
  const fetchTolls = useCallback(async () => {
    setIsLoadingToll(true);
    try {
      const res = await api.estimateRouteToll({
        route_distance_km: distanceKm,
        encoded_polyline: encodedPolyline,
        route_geometry: routeGeometry,
        vehicle_type: selectedVehicleType,
        is_round_trip: isRoundTrip,
      });
      setTollEstimate(res);
    } catch {
      // Graceful fallback: Never fabricate toll data
      setTollEstimate({
        status: 'unavailable',
        provider: 'none',
        total_toll: null,
        currency: 'INR',
        plazas: [],
        is_confirmed: false,
        is_estimated: false,
        source: 'none',
        message: 'Toll estimate unavailable: Could not reach backend toll service.',
      });
    } finally {
      setIsLoadingToll(false);
    }
  }, [distanceKm, encodedPolyline, routeGeometry, selectedVehicleType, isRoundTrip]);

  useEffect(() => {
    fetchTolls();
  }, [fetchTolls]);

  // Compute Instantaneous Client Budget (pure formula, immediate recalculation)
  const budgetResult = useMemo(() => {
    return computeClientJourneyBudget({
      distanceKm,
      fuelEfficiencyKmPerUnit: efficiencyNum,
      fuelPricePerUnit: priceNum,
      isRoundTrip,
      vehicleLabel:
        selectedVehicleType === 'custom'
          ? customVehicleName.trim() || 'Custom Vehicle'
          : activeVehiclePreset.label,
      fuelType: activeFuelPreset.label,
      fuelUnit: activeFuelPreset.unit,
      tollAmount: tollEstimate?.status === 'available' ? tollEstimate.total_toll : null,
      tollSource: tollEstimate?.source,
      isTollConfirmed: tollEstimate?.is_confirmed,
    });
  }, [
    distanceKm,
    efficiencyNum,
    priceNum,
    isRoundTrip,
    selectedVehicleType,
    customVehicleName,
    activeVehiclePreset.label,
    activeFuelPreset.label,
    activeFuelPreset.unit,
    tollEstimate,
  ]);

  return (
    <div
      id="journey-budget-calculator"
      style={{
        marginTop: '16px',
        padding: '16px',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-medium)',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
      }}
    >
      {/* Title & Route Distance Indicator */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#10b981',
            }}
          >
            <Fuel size={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Fuel Cost & Journey Budget
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {originName && destinationName ? `${originName} ➔ ${destinationName} • ` : ''}
              <strong>{distanceKm.toFixed(1)} km</strong> {routeSummary ? `via ${routeSummary}` : ''}
            </span>
          </div>
        </div>


        {/* Round Trip Toggle Switch */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            id="btn-toggle-round-trip"
            onClick={() => setIsRoundTrip(!isRoundTrip)}
            className="btn btn-secondary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              padding: '5px 10px',
              borderRadius: 'var(--radius-full)',
              background: isRoundTrip ? 'var(--primary-600)' : 'var(--bg-tertiary)',
              color: isRoundTrip ? '#ffffff' : 'var(--text-secondary)',
              border: isRoundTrip ? '1px solid var(--primary-500)' : '1px solid var(--border-subtle)',
            }}
          >
            <RotateCcw size={12} />
            <span>{isRoundTrip ? 'Round-Trip (2×)' : 'One-Way'}</span>
          </button>
        </div>
      </div>

      {/* Row 1: Vehicle Type Selection Pills */}
      <div>
        <label
          style={{
            display: 'block',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '6px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}
        >
          Vehicle Category
        </label>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
            gap: '6px',
          }}
        >
          {VEHICLE_PRESETS.map((preset) => {
            const isSelected = selectedVehicleType === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                id={`btn-vehicle-${preset.id}`}
                onClick={() => handleSelectVehicle(preset)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  padding: '7px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #10b981' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-tertiary)',
                  color: isSelected ? '#10b981' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease',
                }}
                title={preset.description}
              >
                {preset.id === 'motorcycle' && <Bike size={14} />}
                {preset.id === 'car' && <Car size={14} />}
                {preset.id === 'suv' && <Truck size={14} />}
                {preset.id === 'custom' && <Sliders size={14} />}
                <span>{preset.label.split('/')[0].trim()}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom vehicle name input if custom selected */}
      {selectedVehicleType === 'custom' && (
        <div>
          <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
            Custom Vehicle Name:
          </label>
          <input
            type="text"
            id="input-custom-vehicle-name"
            className="input-text"
            value={customVehicleName}
            onChange={(e) => setCustomVehicleName(e.target.value)}
            placeholder="e.g. Vintage Van, Commercial Bus..."
            style={{ fontSize: '12px', padding: '6px 10px' }}
          />
        </div>
      )}

      {/* Row 2: Fuel Type Selection Pills */}
      <div>
        <label
          style={{
            display: 'block',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '6px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}
        >
          Fuel / Energy Type
        </label>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {FUEL_PRESETS.map((preset) => {
            const isSelected = selectedFuelType === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                id={`btn-fuel-${preset.id}`}
                onClick={() => handleSelectFuel(preset)}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #38bdf8' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-tertiary)',
                  color: isSelected ? '#38bdf8' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease',
                }}
              >
                {preset.label} ({preset.unit})
              </button>
            );
          })}
        </div>
      </div>

      {/* Row 3: Numeric Inputs (Efficiency & Price) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '12px',
        }}
      >
        {/* Fuel Efficiency Input */}
        <div>
          <label
            htmlFor="input-fuel-efficiency"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}
          >
            <span>Mileage / Efficiency</span>
            <span style={{ color: 'var(--text-muted)' }}>km / {activeFuelPreset.unit}</span>
          </label>
          <input
            type="number"
            id="input-fuel-efficiency"
            className="input-text"
            step="0.1"
            min="0.1"
            max="200"
            value={efficiencyInput}
            onChange={(e) => setEfficiencyInput(e.target.value)}
            style={{
              fontSize: '13px',
              padding: '7px 10px',
              borderColor: efficiencyNum <= 0 ? 'var(--status-red)' : undefined,
            }}
          />
          {efficiencyNum <= 0 && (
            <span style={{ fontSize: '10px', color: 'var(--status-red)', marginTop: '2px', display: 'block' }}>
              Efficiency must be &gt; 0 km/{activeFuelPreset.unit}
            </span>
          )}
        </div>

        {/* Fuel Price Input */}
        <div>
          <label
            htmlFor="input-fuel-price"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}
          >
            <span>Fuel Price</span>
            <span style={{ color: 'var(--text-muted)' }}>₹ / {activeFuelPreset.unit}</span>
          </label>
          <input
            type="number"
            id="input-fuel-price"
            className="input-text"
            step="0.5"
            min="0"
            value={priceInput}
            onChange={(e) => setPriceInput(e.target.value)}
            style={{
              fontSize: '13px',
              padding: '7px 10px',
              borderColor: priceNum < 0 ? 'var(--status-red)' : undefined,
            }}
          />
          {priceNum < 0 && (
            <span style={{ fontSize: '10px', color: 'var(--status-red)', marginTop: '2px', display: 'block' }}>
              Price cannot be negative
            </span>
          )}
        </div>
      </div>

      {/* Validation Banner if Inputs Invalid */}
      {!budgetResult.isValid && budgetResult.errorMessage && (
        <div
          id="budget-validation-warning"
          style={{
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--status-red)',
            color: 'var(--status-red)',
            fontSize: '11px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <AlertTriangle size={14} />
          <span>{budgetResult.errorMessage}</span>
        </div>
      )}

      {/* Row 4: Results & Breakdown Cards */}
      {budgetResult.isValid && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* 3 Metric Cards: One-Way Fuel, Return Fuel, Toll Status */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: '8px',
            }}
          >
            {/* One-Way Fuel Cost */}
            <div
              style={{
                background: 'var(--bg-tertiary)',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: !isRoundTrip ? '1px solid #10b981' : '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                One-Way Fuel
              </span>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                {formatCurrency(budgetResult.oneWayFuelCost)}
              </div>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                ~{(distanceKm / efficiencyNum).toFixed(2)} {activeFuelPreset.unit} req.
              </span>
            </div>

            {/* Return Trip Fuel Cost */}
            <div
              style={{
                background: 'var(--bg-tertiary)',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: isRoundTrip ? '1px solid #10b981' : '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Return-Trip Fuel
              </span>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                {formatCurrency(budgetResult.returnTripFuelCost)}
              </div>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                ~{((distanceKm * 2) / efficiencyNum).toFixed(2)} {activeFuelPreset.unit} req.
              </span>
            </div>

            {/* Toll Estimate Card */}
            <div
              style={{
                background: 'var(--bg-tertiary)',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Highway Tolls
                </span>
                {isLoadingToll && <RefreshCw size={10} className="spin" color="var(--text-muted)" />}
              </div>

              {tollEstimate?.status === 'available' && tollEstimate.total_toll !== null ? (
                <>
                  <div style={{ fontSize: '16px', fontWeight: 700, color: '#f59e0b', marginTop: '2px' }}>
                    {formatCurrency(tollEstimate.total_toll)}
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {tollEstimate.plazas.length} plaza(s) ({tollEstimate.is_confirmed ? 'Confirmed' : 'Estimated'})
                  </span>
                </>
              ) : (
                <>
                  <div
                    id="toll-status-badge-unavailable"
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      marginTop: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <span>Toll estimate unavailable</span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    No verified provider key
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Prominent Total Estimated Journey Budget Banner */}
          <div
            id="journey-budget-total-card"
            style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(56, 189, 248, 0.12) 100%)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <div>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  color: '#10b981',
                }}
              >
                Estimated Total Journey Budget ({isRoundTrip ? 'Round-Trip' : 'One-Way'})
              </span>
              <div
                id="journey-budget-total-amount"
                style={{
                  fontSize: '24px',
                  fontWeight: 800,
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.5px',
                  marginTop: '2px',
                }}
              >
                {formatCurrency(budgetResult.totalCost)}
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {tollEstimate?.status === 'available' && tollEstimate.total_toll !== null
                  ? `Includes fuel (${formatCurrency(budgetResult.activeFuelCost)}) + tolls (${formatCurrency(tollEstimate.total_toll)})`
                  : `Includes fuel (${formatCurrency(budgetResult.activeFuelCost)}) • Excludes tolls (data unavailable)`}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <span
                style={{
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '10px',
                  fontWeight: 600,
                  background: 'rgba(16, 185, 129, 0.2)',
                  color: '#10b981',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                }}
              >
                {budgetResult.fuelRequiredUnits.toFixed(2)} {activeFuelPreset.unit} Total Fuel
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                Effective distance: {budgetResult.effectiveDistanceKm.toFixed(1)} km
              </span>
            </div>
          </div>

          {/* Transparent Assumptions & Calculation Disclosures */}
          <div
            style={{
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-tertiary)',
              overflow: 'hidden',
            }}
          >
            <button
              type="button"
              id="btn-toggle-assumptions"
              onClick={() => setShowAssumptions(!showAssumptions)}
              style={{
                width: '100%',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                fontSize: '11px',
                fontWeight: 600,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={13} color="var(--primary-500)" />
                <span>Assumptions & Calculation Disclosures ({budgetResult.assumptions.length})</span>
              </div>
              {showAssumptions ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showAssumptions && (
              <div
                id="budget-assumptions-list"
                style={{
                  padding: '8px 14px 12px 14px',
                  borderTop: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4,
                }}
              >
                {budgetResult.assumptions.map((assumption: string, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                    <span style={{ color: '#10b981', fontWeight: 700 }}>•</span>
                    <span>{assumption}</span>
                  </div>
                ))}

                <div style={{ marginTop: '4px', fontSize: '10px', color: 'var(--text-muted)' }}>
                  * No personal tracking or origin-destination identity is stored. Calculations are performed on-demand.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
