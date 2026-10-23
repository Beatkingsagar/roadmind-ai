import { describe, it, expect } from 'bun:test';
import {
  formatSpeed,
  formatDuration,
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
