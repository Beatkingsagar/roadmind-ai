import { getCongestionColor, getCongestionLabel } from './constants';
export { getCongestionColor, getCongestionLabel };

export function formatSpeed(mps: number | null | undefined, unit: 'kmph' | 'mps' = 'kmph'): string {
  if (mps === null || mps === undefined) return 'N/A';
  if (unit === 'kmph') {
    const kmph = Math.round(mps * 3.6 * 10) / 10;
    return `${kmph} km/h`;
  }
  return `${Math.round(mps * 10) / 10} m/s`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return 'Unreachable';
  }
  if (seconds === 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

export function formatHoursAndMinutes(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return 'Unreachable';
  }
  const totalMins = Math.round(seconds / 60);
  if (totalMins < 60) return `${totalMins} min`;
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  return mins > 0 ? `${hours} hr ${mins} min` : `${hours} hr`;
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined || !Number.isFinite(meters)) {
    return '0 m';
  }
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`;
  }
  return `${Math.round(meters)} m`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export function formatTimeOnly(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export function getOutcomeBadgeProps(outcome: string | undefined): {
  label: string;
  variant: 'emerald' | 'amber' | 'red' | 'slate';
  description: string;
} {
  switch (outcome) {
    case 'ROBUST_ALTERNATIVE':
      return {
        label: 'Robust Alternative Route',
        variant: 'emerald',
        description: 'Alternative route is faster across all tested scenarios (both slowdown and full closure).',
      };
    case 'EVIDENCE_SENSITIVE':
      return {
        label: 'Evidence-Sensitive Recommendation',
        variant: 'amber',
        description: 'Preferred route flips between slowdown and closure; verifying incident blockage is critical.',
      };
    case 'NO_ROUTE_AVAILABLE':
      return {
        label: 'No Alternative Route Available',
        variant: 'red',
        description: 'Corridor closure leaves destination unreachable via network.',
      };
    case 'INSUFFICIENT_DATA':
    default:
      return {
        label: 'Insufficient Data / Disconnected',
        variant: 'slate',
        description: 'Available network connectivity is insufficient for reliable routing comparison.',
      };
  }
}

// ============================================================================
// Phase 5: Currency Formatting & Instantaneous Client Budget Computation
// ============================================================================

export function formatCurrency(
  amount: number | null | undefined,
  currency: string = 'INR'
): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return 'Unavailable';
  }
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `₹${amount.toFixed(2)}`;
  }
}

export interface ClientBudgetResult {
  isValid: boolean;
  errorMessage: string | null;
  effectiveDistanceKm: number;
  fuelRequiredUnits: number;
  oneWayFuelCost: number;
  returnTripFuelCost: number;
  activeFuelCost: number;
  totalCost: number;
  assumptions: string[];
}

export function computeClientJourneyBudget(params: {
  distanceKm: number;
  fuelEfficiencyKmPerUnit: number;
  fuelPricePerUnit: number;
  isRoundTrip: boolean;
  vehicleLabel: string;
  fuelType: string;
  fuelUnit: string;
  tollAmount: number | null;
  tollSource?: string;
  isTollConfirmed?: boolean;
}): ClientBudgetResult {
  const {
    distanceKm,
    fuelEfficiencyKmPerUnit,
    fuelPricePerUnit,
    isRoundTrip,
    vehicleLabel,
    fuelType,
    fuelUnit,
    tollAmount,
    tollSource,
    isTollConfirmed,
  } = params;

  if (distanceKm <= 0 || !Number.isFinite(distanceKm)) {
    return {
      isValid: false,
      errorMessage: 'Route distance must be greater than 0 km.',
      effectiveDistanceKm: 0,
      fuelRequiredUnits: 0,
      oneWayFuelCost: 0,
      returnTripFuelCost: 0,
      activeFuelCost: 0,
      totalCost: 0,
      assumptions: [],
    };
  }

  if (fuelEfficiencyKmPerUnit <= 0 || !Number.isFinite(fuelEfficiencyKmPerUnit)) {
    return {
      isValid: false,
      errorMessage: 'Fuel efficiency must be a positive number greater than 0.',
      effectiveDistanceKm: isRoundTrip ? distanceKm * 2 : distanceKm,
      fuelRequiredUnits: 0,
      oneWayFuelCost: 0,
      returnTripFuelCost: 0,
      activeFuelCost: 0,
      totalCost: 0,
      assumptions: [],
    };
  }

  if (fuelPricePerUnit < 0 || !Number.isFinite(fuelPricePerUnit)) {
    return {
      isValid: false,
      errorMessage: 'Fuel price cannot be negative.',
      effectiveDistanceKm: isRoundTrip ? distanceKm * 2 : distanceKm,
      fuelRequiredUnits: 0,
      oneWayFuelCost: 0,
      returnTripFuelCost: 0,
      activeFuelCost: 0,
      totalCost: 0,
      assumptions: [],
    };
  }

  const effectiveDistanceKm = Math.round((isRoundTrip ? distanceKm * 2 : distanceKm) * 100) / 100;
  const oneWayFuel = distanceKm / fuelEfficiencyKmPerUnit;
  const oneWayCost = Math.round(oneWayFuel * fuelPricePerUnit * 100) / 100;

  const returnTripFuel = (distanceKm * 2) / fuelEfficiencyKmPerUnit;
  const returnTripCost = Math.round(returnTripFuel * fuelPricePerUnit * 100) / 100;

  const activeFuelRequired = Math.round((isRoundTrip ? returnTripFuel : oneWayFuel) * 100) / 100;
  const activeFuelCost = isRoundTrip ? returnTripCost : oneWayCost;

  const effectiveToll = tollAmount !== null && Number.isFinite(tollAmount) ? tollAmount : 0;
  const totalCost = Math.round((activeFuelCost + effectiveToll) * 100) / 100;

  const assumptions: string[] = [
    `Route distance: ${distanceKm.toFixed(2)} km (from real-world road routing provider)`,
    isRoundTrip
      ? `Trip mode: Round-trip (2× distance = ${effectiveDistanceKm.toFixed(2)} km)`
      : 'Trip mode: One-way journey',
    `Vehicle: ${vehicleLabel} (${fuelEfficiencyKmPerUnit.toFixed(1)} km/${fuelUnit})`,
    `Fuel: ${fuelType.toUpperCase()} at ₹${fuelPricePerUnit.toFixed(2)} per ${fuelUnit}`,
    `Formula: Fuel required (${activeFuelRequired.toFixed(2)} ${fuelUnit}) = Distance (${effectiveDistanceKm.toFixed(2)} km) ÷ Efficiency (${fuelEfficiencyKmPerUnit.toFixed(1)} km/${fuelUnit})`,
    `Formula: Fuel cost (₹${activeFuelCost.toFixed(2)}) = Fuel required × Fuel price (₹${fuelPricePerUnit.toFixed(2)})`,
  ];

  if (tollAmount !== null && tollAmount > 0) {
    const statusText = isTollConfirmed ? 'confirmed published rate' : 'estimated rate';
    assumptions.push(`Tolls included: ₹${tollAmount.toFixed(2)} (${statusText}) via ${tollSource || 'Toll Provider'}`);
  } else {
    assumptions.push('Tolls excluded: Toll estimate unavailable (no verified toll provider configured). Total reflects fuel expenses only.');
  }

  return {
    isValid: true,
    errorMessage: null,
    effectiveDistanceKm,
    fuelRequiredUnits: activeFuelRequired,
    oneWayFuelCost: oneWayCost,
    returnTripFuelCost: returnTripCost,
    activeFuelCost,
    totalCost,
    assumptions,
  };
}

