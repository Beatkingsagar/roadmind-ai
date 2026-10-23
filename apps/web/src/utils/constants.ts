/**
 * RoadMind AI — Supported network constants, place definitions, and demo presets.
 */

export interface SupportedNode {
  id: string;
  name: string;
  shortName: string;
  description: string;
  coordinates: [number, number]; // [lat, lon] for Leaflet map markers
}

export const SUPPORTED_NODES: SupportedNode[] = [
  {
    id: 'node_origin',
    name: 'West Transit Terminal (Origin Node)',
    shortName: 'West Terminal',
    description: 'Western commuter ingress junction (Grand Corridor / Bypass split)',
    coordinates: [40.748, -73.985],
  },
  {
    id: 'node_corridor_mid',
    name: 'Central Plaza Junction (Mid Corridor)',
    shortName: 'Central Plaza',
    description: 'Core urban crossroads between West Corridor, East Corridor & North Blvd',
    coordinates: [40.75, -73.98],
  },
  {
    id: 'node_destination',
    name: 'Civic Center Hub (Destination Node)',
    shortName: 'Civic Center',
    description: 'Downtown commercial terminal and destination hub',
    coordinates: [40.752, -73.975],
  },
  {
    id: 'node_bypass_mid',
    name: 'South Bypass Interchange',
    shortName: 'South Bypass',
    description: 'High-speed southern bypass avoiding downtown corridor',
    coordinates: [40.745, -73.98],
  },
  {
    id: 'node_hub_north',
    name: 'North Boulevard Terminal',
    shortName: 'North Terminal',
    description: 'End of one-way northbound boulevard (local class)',
    coordinates: [40.756, -73.978],
  },
  {
    id: 'node_stale_zone',
    name: 'Industrial Sector Spur',
    shortName: 'Industrial Spur',
    description: 'Freight access road characterized by sparse sensor observations',
    coordinates: [40.749, -73.97],
  },
  {
    id: 'node_isolated',
    name: 'East Sector Outpost (Isolated Node)',
    shortName: 'East Outpost',
    description: 'Restricted perimeter zone with disconnected baseline routing',
    coordinates: [40.76, -73.96],
  },
];

export const DEMO_PRESETS = [
  {
    name: 'Corridor Peak Incident (Recommended Demo)',
    description: 'Accident on Grand Corridor East; evaluates Robust Alternative bypass route',
    origin: 'node_origin',
    destination: 'node_destination',
    incidentSegmentId: 'seg_corridor_e',
    timestamp: '2026-10-15T08:30:00Z',
  },
  {
    name: 'Baseline Free-Flow (Early Morning)',
    description: 'Clear roads before morning rush hour; all segments at free-flow speed',
    origin: 'node_origin',
    destination: 'node_destination',
    incidentSegmentId: undefined,
    timestamp: '2026-10-15T07:30:00Z',
  },
  {
    name: 'Post-Incident Outcome Evaluation',
    description: 'Accident cleared; actual observations revealed to score predictions',
    origin: 'node_origin',
    destination: 'node_destination',
    incidentSegmentId: undefined,
    timestamp: '2026-10-15T09:15:00Z',
  },
];

export const MAP_CENTER: [number, number] = [40.751, -73.978];
export const MAP_DEFAULT_ZOOM = 14;

export const CONGESTION_COLORS = {
  freeFlow: '#10b981', // Emerald 500 (>= 0.85)
  moderate: '#f59e0b', // Amber 500 (0.60 - 0.84)
  heavy: '#f97316',    // Orange 500 (0.30 - 0.59)
  severe: '#ef4444',   // Red 500 (< 0.30 / blocked)
  unknown: '#94a3b8',  // Slate 400
};

export function getCongestionColor(ratio: number): string {
  if (ratio >= 0.85) return CONGESTION_COLORS.freeFlow;
  if (ratio >= 0.6) return CONGESTION_COLORS.moderate;
  if (ratio >= 0.3) return CONGESTION_COLORS.heavy;
  return CONGESTION_COLORS.severe;
}

export function getCongestionLabel(ratio: number): string {
  if (ratio >= 0.85) return 'Free-Flow';
  if (ratio >= 0.6) return 'Moderate Slowdown';
  if (ratio >= 0.3) return 'Heavy Congestion';
  return 'Severe Delay / Blocked';
}
