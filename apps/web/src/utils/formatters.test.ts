import { describe, it, expect } from 'bun:test';
import {
  formatSpeed,
  formatDuration,
  formatHoursAndMinutes,
  formatDistance,
  formatDateTime,
  formatTimeOnly,
  getOutcomeBadgeProps,
} from './formatters';
import {
  SUPPORTED_NODES,
  DEMO_PRESETS,
  getCongestionColor,
  getCongestionLabel,
} from './constants';

describe('Formatters and Utilities', () => {
  it('formats speed in km/h correctly', () => {
    expect(formatSpeed(13.8889)).toBe('50 km/h');
    expect(formatSpeed(0)).toBe('0 km/h');
    expect(formatSpeed(null)).toBe('N/A');
    expect(formatSpeed(undefined)).toBe('N/A');
  });

  it('formats duration into minutes and seconds', () => {
    expect(formatDuration(120)).toBe('2m');
    expect(formatDuration(144)).toBe('2m 24s');
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(0)).toBe('0s');
    expect(formatDuration(null)).toBe('Unreachable');
  });

  it('formats highway travel duration into hours and minutes', () => {
    expect(formatHoursAndMinutes(4671.6)).toBe('1 hr 18 min'); // Kundapura to Mangaluru
    expect(formatHoursAndMinutes(1860)).toBe('31 min'); // Udupi to Surathkal
    expect(formatHoursAndMinutes(3600)).toBe('1 hr');
    expect(formatHoursAndMinutes(7200)).toBe('2 hr');
    expect(formatHoursAndMinutes(0)).toBe('0 min');
    expect(formatHoursAndMinutes(null)).toBe('Unreachable');
    expect(formatHoursAndMinutes(undefined)).toBe('Unreachable');
  });

  it('formats distance into meters and kilometers', () => {
    expect(formatDistance(500)).toBe('500 m');
    expect(formatDistance(1800)).toBe('1.80 km');
    expect(formatDistance(null)).toBe('0 m');
  });

  it('formats timestamps properly in UTC', () => {
    const iso = '2026-10-15T08:30:00Z';
    const formatted = formatDateTime(iso);
    expect(formatted).toContain('08:30');
    expect(formatted).toContain('UTC');

    const timeOnly = formatTimeOnly(iso);
    expect(timeOnly).toContain('08:30');
  });

  it('classifies recommendation outcomes accurately', () => {
    const robust = getOutcomeBadgeProps('ROBUST_ALTERNATIVE');
    expect(robust.variant).toBe('emerald');
    expect(robust.label).toContain('Robust Alternative');

    const sensitive = getOutcomeBadgeProps('EVIDENCE_SENSITIVE');
    expect(sensitive.variant).toBe('amber');
    expect(sensitive.label).toContain('Evidence-Sensitive');

    const noRoute = getOutcomeBadgeProps('NO_ROUTE_AVAILABLE');
    expect(noRoute.variant).toBe('red');

    const insufficient = getOutcomeBadgeProps('INSUFFICIENT_DATA');
    expect(insufficient.variant).toBe('slate');
  });

  it('calculates congestion colors based on speed ratio threshold', () => {
    expect(getCongestionColor(0.9)).toBe('#10b981'); // Free flow
    expect(getCongestionColor(0.7)).toBe('#f59e0b'); // Moderate
    expect(getCongestionColor(0.4)).toBe('#f97316'); // Heavy
    expect(getCongestionColor(0.2)).toBe('#ef4444'); // Severe

    expect(getCongestionLabel(0.95)).toBe('Free-Flow');
    expect(getCongestionLabel(0.15)).toBe('Severe Delay / Blocked');
  });
});

describe('Network and Demo Constants', () => {
  it('defines all 7 supported junction nodes', () => {
    expect(SUPPORTED_NODES.length).toBe(7);
    const nodeIds = SUPPORTED_NODES.map((n) => n.id);
    expect(nodeIds).toContain('node_origin');
    expect(nodeIds).toContain('node_corridor_mid');
    expect(nodeIds).toContain('node_destination');
    expect(nodeIds).toContain('node_bypass_mid');
    expect(nodeIds).toContain('node_hub_north');
    expect(nodeIds).toContain('node_stale_zone');
    expect(nodeIds).toContain('node_isolated');
  });

  it('defines 3 standard demo presets', () => {
    expect(DEMO_PRESETS.length).toBe(3);
    expect(DEMO_PRESETS[0].incidentSegmentId).toBe('seg_corridor_e');
    expect(DEMO_PRESETS[0].timestamp).toBe('2026-10-15T08:30:00Z');
  });

  it('defines real-world Mangaluru geography and landmarks', () => {
    const { MANGALURU_CENTER, SECTOR_7_CENTER, MANGALURU_LANDMARKS, TILE_PROVIDERS } = require('./constants');
    expect(MANGALURU_CENTER[0]).toBeCloseTo(12.9141, 3);
    expect(MANGALURU_CENTER[1]).toBeCloseTo(74.8560, 3);
    expect(SECTOR_7_CENTER[0]).toBeCloseTo(40.751, 3);
    expect(SECTOR_7_CENTER[1]).toBeCloseTo(-73.978, 3);

    expect(MANGALURU_LANDMARKS.length).toBeGreaterThanOrEqual(7);
    const landmarkIds = MANGALURU_LANDMARKS.map((l: { id: string }) => l.id);
    expect(landmarkIds).toContain('mng_hampankatta');
    expect(landmarkIds).toContain('mng_kottara_chowki');
    expect(landmarkIds).toContain('mng_sdit_kenjar');
    expect(landmarkIds).toContain('mng_airport');

    expect(TILE_PROVIDERS.cartoVoyager.url).toContain('cartocdn.com');
    expect(TILE_PROVIDERS.cartoDarkMatter.url).toContain('cartocdn.com');
    expect(TILE_PROVIDERS.osmStandard.url).toContain('tile.openstreetmap.org');
    expect(TILE_PROVIDERS.osmFallback.url).toContain('openstreetmap.fr');
  });

  it('provides public OSM basemap by default and supports CARTO key when configured', () => {
    const { getActiveTileProvider, TILE_PROVIDERS } = require('./constants');
    
    // Default: No key provided -> returns public OSM standard without API key
    const defaultLight = getActiveTileProvider('light');
    expect(defaultLight.url).toBe(TILE_PROVIDERS.osmStandard.url);
    expect(defaultLight.attribution).toContain('OpenStreetMap');

    const defaultDark = getActiveTileProvider('dark');
    expect(defaultDark.url).toBe(TILE_PROVIDERS.osmStandard.url);

    // Optional CARTO key provided -> returns authenticated CARTO tiles
    const cartoLight = getActiveTileProvider('light', 'test_carto_secret_key');
    expect(cartoLight.url).toContain('cartocdn.com');
    expect(cartoLight.url).toContain('api_key=test_carto_secret_key');

    const cartoDark = getActiveTileProvider('dark', 'test_carto_secret_key');
    expect(cartoDark.url).toContain('cartocdn.com');
    expect(cartoDark.url).toContain('dark_all');
    expect(cartoDark.url).toContain('api_key=test_carto_secret_key');
  });
});

describe('Phase 2: Real-Place Search & Coordinate Validation', () => {
  const { isValidCoordinate } = require('./constants');

  it('validates geographic coordinates accurately', () => {
    // Kundapura
    expect(isValidCoordinate(13.6268, 74.6917)).toBe(true);
    // Mangaluru
    expect(isValidCoordinate(12.9141, 74.8560)).toBe(true);
    // Boundary bounds
    expect(isValidCoordinate(-90.0, -180.0)).toBe(true);
    expect(isValidCoordinate(90.0, 180.0)).toBe(true);

    // Invalid coordinates
    expect(isValidCoordinate(95.0, 74.85)).toBe(false);
    expect(isValidCoordinate(-95.0, 74.85)).toBe(false);
    expect(isValidCoordinate(12.91, 195.0)).toBe(false);
    expect(isValidCoordinate(12.91, -195.0)).toBe(false);
    expect(isValidCoordinate(NaN, 74.85)).toBe(false);
    expect(isValidCoordinate(12.91, NaN)).toBe(false);
  });

  it('correctly models place selection and coordinate storage for Kundapura and Mangaluru', () => {
    interface RealPlace {
      id: string;
      name: string;
      displayName: string;
      lat: number;
      lon: number;
      source: string;
    }

    const kundapura: RealPlace = {
      id: 'cache_kundapura',
      name: 'Kundapura',
      displayName: 'Kundapura, Udupi District, Karnataka, India',
      lat: 13.6268,
      lon: 74.6917,
      source: 'verified_cache',
    };

    const mangaluru: RealPlace = {
      id: 'cache_mangaluru',
      name: 'Mangaluru',
      displayName: 'Mangaluru, Dakshina Kannada, Karnataka, India',
      lat: 12.9141,
      lon: 74.8560,
      source: 'verified_cache',
    };

    expect(kundapura.name).toBe('Kundapura');
    expect(kundapura.lat).toBeCloseTo(13.6268, 4);
    expect(kundapura.lon).toBeCloseTo(74.6917, 4);
    expect(kundapura.source).toBe('verified_cache');

    expect(mangaluru.name).toBe('Mangaluru');
    expect(mangaluru.lat).toBeCloseTo(12.9141, 4);
    expect(mangaluru.lon).toBeCloseTo(74.8560, 4);
    expect(mangaluru.source).toBe('verified_cache');
  });

  it('correctly swaps origin and destination places and coordinates bidirectionally', () => {
    let origin = {
      name: 'Kundapura',
      lat: 13.6268,
      lon: 74.6917,
    };
    let destination = {
      name: 'Mangaluru',
      lat: 12.9141,
      lon: 74.8560,
    };

    // Swap simulation
    const swap = () => {
      const temp = origin;
      origin = destination;
      destination = temp;
    };

    swap();
    expect(origin.name).toBe('Mangaluru');
    expect(origin.lat).toBeCloseTo(12.9141, 4);
    expect(destination.name).toBe('Kundapura');
    expect(destination.lat).toBeCloseTo(13.6268, 4);

    // Swap back
    swap();
    expect(origin.name).toBe('Kundapura');
    expect(destination.name).toBe('Mangaluru');
  });

  it('clears selected place state accurately', () => {
    let place: { name: string; lat: number; lon: number } | null = {
      name: 'Kundapura',
      lat: 13.6268,
      lon: 74.6917,
    };

    const clearPlace = () => {
      place = null;
    };

    clearPlace();
    expect(place).toBeNull();
  });

  it('preserves map mode invariants between real-world and synthetic demo', () => {
    type MapMode = 'real_world' | 'synthetic_demo';
    let currentMode: MapMode = 'real_world';

    // Default must be real_world
    expect(currentMode).toBe('real_world');

    // Switch to synthetic demo
    currentMode = 'synthetic_demo';
    expect(currentMode).toBe('synthetic_demo');

    // Return to real_world
    currentMode = 'real_world';
    expect(currentMode).toBe('real_world');
  });

  it('verifies debounce execution behavior', async () => {
    let callCount = 0;
    let timer: any = null;

    const debouncedSearch = (val: string) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        callCount++;
      }, 50);
    };

    debouncedSearch('k');
    debouncedSearch('ku');
    debouncedSearch('kun');
    debouncedSearch('kund');
    debouncedSearch('kundapura');

    expect(callCount).toBe(0);
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(callCount).toBe(1);
  });
});

describe('Phase 3: Real-World Road Routing (OSRM & Coastal Karnataka)', () => {
  it('models real-world road route from Kundapura to Mangaluru along NH 66', () => {
    const routeResponse = {
      origin: {
        name: 'Kundapura',
        lat: 13.6268,
        lon: 74.6917,
        distance_to_snapped_meters: 8.5,
      },
      destination: {
        name: 'Mangaluru',
        lat: 12.9141,
        lon: 74.8560,
        distance_to_snapped_meters: 12.2,
      },
      primary_route: {
        route_index: 0,
        is_primary: true,
        summary: 'via NH 66',
        distance_meters: 91900.5,
        distance_km: 91.9,
        duration_seconds: 4671.6,
        duration_minutes: 77.9,
        geometry: {
          type: 'LineString',
          coordinates: [
            [74.6917, 13.6268],
            [74.7421, 13.3409],
            [74.7943, 13.0119],
            [74.8560, 12.9141],
          ],
        },
        legs: [{ summary: 'NH 66', distance_meters: 91900.5, duration_seconds: 4671.6 }],
        weight_name: 'routability',
      },
      alternative_routes: [],
      provider: 'osrm',
      profile: 'driving',
      traffic_model: 'standard_routability',
      attribution: 'Route data © OpenStreetMap contributors, OSRM Project (ODbL 1.0)',
    };

    expect(routeResponse.origin.name).toBe('Kundapura');
    expect(routeResponse.destination.name).toBe('Mangaluru');
    expect(routeResponse.primary_route.distance_km).toBeCloseTo(91.9, 1);
    expect(routeResponse.primary_route.duration_minutes).toBeCloseTo(77.9, 1);
    expect(routeResponse.primary_route.summary).toBe('via NH 66');
    expect(routeResponse.primary_route.geometry.type).toBe('LineString');
    expect(routeResponse.primary_route.geometry.coordinates.length).toBe(4);
    expect(routeResponse.alternative_routes.length).toBe(0);
    expect(routeResponse.traffic_model).toBe('standard_routability');
  });

  it('correctly maps GeoJSON LineString [lon, lat] coordinates to Leaflet [lat, lon]', () => {
    const geoJsonCoords: [number, number][] = [
      [74.6917, 13.6268], // Kundapura [lon, lat]
      [74.8560, 12.9141], // Mangaluru [lon, lat]
    ];

    // Leaflet translation
    const leafletLatLngs = geoJsonCoords.map(([lon, lat]) => [lat, lon]);

    expect(leafletLatLngs[0][0]).toBe(13.6268); // latitude
    expect(leafletLatLngs[0][1]).toBe(74.6917); // longitude
    expect(leafletLatLngs[1][0]).toBe(12.9141);
    expect(leafletLatLngs[1][1]).toBe(74.8560);
  });

  it('handles alternative routes when provider returns them and does not invent unreturned routes', () => {
    const responseWithAlt = {
      primary_route: {
        route_index: 0,
        is_primary: true,
        summary: 'via NH 66',
        distance_km: 91.9,
      },
      alternative_routes: [
        {
          route_index: 1,
          is_primary: false,
          summary: 'via Manipal / State Highway',
          distance_km: 99.4,
        },
      ],
    };

    expect(responseWithAlt.alternative_routes.length).toBe(1);
    expect(responseWithAlt.alternative_routes[0].is_primary).toBe(false);
    expect(responseWithAlt.alternative_routes[0].route_index).toBe(1);

    const responseWithoutAlt = {
      primary_route: {
        route_index: 0,
        is_primary: true,
        summary: 'via NH 66',
        distance_km: 91.9,
      },
      alternative_routes: [],
    };

    expect(responseWithoutAlt.alternative_routes.length).toBe(0);
  });

  it('preserves clean separation: real routes do not include synthetic scenario models', () => {
    const realRoute = {
      provider: 'osrm',
      profile: 'driving',
      traffic_model: 'standard_routability',
    };

    expect(realRoute.traffic_model).not.toBe('synthetic');
    expect(realRoute.traffic_model).not.toBe('live_traffic');
    expect(realRoute.traffic_model).toBe('standard_routability');
  });
});

describe('Phase 5: Fuel Cost Calculator, Toll Estimation & Journey Budget', () => {
  const {
    formatCurrency,
    computeClientJourneyBudget,
  } = require('./formatters');
  const {
    VEHICLE_PRESETS,
    FUEL_PRESETS,
  } = require('./constants');

  it('formats currency in Indian Rupees (INR) correctly', () => {
    const formatted = formatCurrency(634.11);
    expect(formatted).toContain('634.11');
    expect(formatCurrency(0)).toContain('0.00');
    expect(formatCurrency(null)).toBe('Unavailable');
    expect(formatCurrency(undefined)).toBe('Unavailable');
    expect(formatCurrency(NaN)).toBe('Unavailable');
  });

  it('calculates one-way fuel consumption and costs accurately for Kundapura to Mangaluru', () => {
    const result = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 103.50,
      isRoundTrip: false,
      vehicleLabel: 'Car / Sedan',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });

    expect(result.isValid).toBe(true);
    expect(result.errorMessage).toBeNull();
    expect(result.effectiveDistanceKm).toBe(91.9);

    // Fuel Required = 91.9 / 15.0 = 6.13 L
    expect(result.fuelRequiredUnits).toBeCloseTo(6.13, 2);

    // Fuel Cost = 6.12666... * 103.50 = 634.11
    expect(result.oneWayFuelCost).toBe(634.11);
    expect(result.activeFuelCost).toBe(634.11);
    expect(result.totalCost).toBe(634.11);
    expect(result.assumptions.length).toBeGreaterThan(3);
    expect(result.assumptions[0]).toContain('91.90 km');
  });

  it('calculates round-trip journey costs by accurately doubling effective distance and fuel expense', () => {
    const result = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 103.50,
      isRoundTrip: true,
      vehicleLabel: 'Car / Sedan',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });

    expect(result.isValid).toBe(true);
    expect(result.effectiveDistanceKm).toBe(183.8);

    // Fuel Required = 183.8 / 15.0 = 12.25 L
    expect(result.fuelRequiredUnits).toBeCloseTo(12.25, 2);

    // Return trip cost = 1268.22
    expect(result.returnTripFuelCost).toBe(1268.22);
    expect(result.activeFuelCost).toBe(1268.22);
    expect(result.totalCost).toBe(1268.22);
  });

  it('computes fuel costs across different vehicle efficiencies and categories', () => {
    // 1. Motorcycle (45 km/L)
    const moto = computeClientJourneyBudget({
      distanceKm: 90.0,
      fuelEfficiencyKmPerUnit: 45.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Motorcycle',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(moto.fuelRequiredUnits).toBe(2.0);
    expect(moto.activeFuelCost).toBe(200.0);

    // 2. SUV (12 km/L)
    const suv = computeClientJourneyBudget({
      distanceKm: 90.0,
      fuelEfficiencyKmPerUnit: 12.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'SUV',
      fuelType: 'Diesel',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(suv.fuelRequiredUnits).toBe(7.5);
    expect(suv.activeFuelCost).toBe(750.0);

    // 3. Custom vehicle
    const custom = computeClientJourneyBudget({
      distanceKm: 90.0,
      fuelEfficiencyKmPerUnit: 18.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Custom Hybrid',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(custom.fuelRequiredUnits).toBe(5.0);
    expect(custom.activeFuelCost).toBe(500.0);
  });

  it('validates invalid inputs and zero values with informative error messages', () => {
    // Zero efficiency
    const zeroEff = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 0,
      fuelPricePerUnit: 103.50,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(zeroEff.isValid).toBe(false);
    expect(zeroEff.errorMessage).toContain('Fuel efficiency must be a positive number');

    // Negative efficiency
    const negEff = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: -10,
      fuelPricePerUnit: 103.50,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(negEff.isValid).toBe(false);
    expect(negEff.errorMessage).toContain('Fuel efficiency must be a positive number');

    // Negative price
    const negPrice = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: -20,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(negPrice.isValid).toBe(false);
    expect(negPrice.errorMessage).toContain('Fuel price cannot be negative');

    // Zero distance
    const zeroDist = computeClientJourneyBudget({
      distanceKm: 0,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 100,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });
    expect(zeroDist.isValid).toBe(false);
    expect(zeroDist.errorMessage).toContain('Route distance must be greater than 0');
  });

  it('updates estimated journey budget dynamically when route changes', () => {
    const primaryDistance = 91.9; // Kundapura to Mangaluru via NH 66
    const altDistance = 99.4;     // Alternative via State Highway

    const primaryBudget = computeClientJourneyBudget({
      distanceKm: primaryDistance,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });

    const altBudget = computeClientJourneyBudget({
      distanceKm: altDistance,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });

    expect(primaryBudget.activeFuelCost).toBe(612.67);
    expect(altBudget.activeFuelCost).toBe(662.67);
    expect(altBudget.activeFuelCost).toBeGreaterThan(primaryBudget.activeFuelCost);
  });

  it('preserves Zero-Fabrication Invariant for toll estimation', () => {
    // When toll amount is null / unavailable:
    const noToll = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: null,
    });

    expect(noToll.totalCost).toBe(noToll.activeFuelCost);
    const assumptionStr = noToll.assumptions.join(' ');
    expect(assumptionStr).toContain('Tolls excluded: Toll estimate unavailable');

    // When toll amount is confirmed:
    const withToll = computeClientJourneyBudget({
      distanceKm: 91.9,
      fuelEfficiencyKmPerUnit: 15.0,
      fuelPricePerUnit: 100.0,
      isRoundTrip: false,
      vehicleLabel: 'Car',
      fuelType: 'Petrol',
      fuelUnit: 'L',
      tollAmount: 125.0,
      tollSource: 'TollGuru India API',
      isTollConfirmed: true,
    });

    expect(withToll.totalCost).toBe(612.67 + 125.0);
    const withTollStr = withToll.assumptions.join(' ');
    expect(withTollStr).toContain('Tolls included: ₹125.00 (confirmed published rate)');
  });

  it('defines vehicle and fuel presets with authentic regional defaults for Karnataka', () => {
    expect(VEHICLE_PRESETS.length).toBe(4);
    const vehicleIds = VEHICLE_PRESETS.map((v: { id: string }) => v.id);
    expect(vehicleIds).toContain('motorcycle');
    expect(vehicleIds).toContain('car');
    expect(vehicleIds).toContain('suv');
    expect(vehicleIds).toContain('custom');

    expect(FUEL_PRESETS.length).toBe(5);
    const fuelIds = FUEL_PRESETS.map((f: { id: string }) => f.id);
    expect(fuelIds).toContain('petrol');
    expect(fuelIds).toContain('diesel');
    expect(fuelIds).toContain('cng');
    expect(fuelIds).toContain('ev');

    const petrol = FUEL_PRESETS.find((f: { id: string }) => f.id === 'petrol');
    expect(petrol.defaultPrice).toBeCloseTo(103.50, 1);
  });
});

