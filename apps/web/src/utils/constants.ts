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

export type MapMode = 'real_world' | 'synthetic_demo';

// Real-World Geography: Mangaluru & Coastal Karnataka (Default Experience)
export const MANGALURU_CENTER: [number, number] = [12.9141, 74.8560];
export const MANGALURU_DEFAULT_ZOOM = 12;

// Synthetic Demo Network (Sector 7 Benchmark)
export const SECTOR_7_CENTER: [number, number] = [40.751, -73.978];
export const SECTOR_7_DEFAULT_ZOOM = 14;

// Default map view defaults to Real-World Mangaluru geography
export const MAP_CENTER: [number, number] = MANGALURU_CENTER;
export const MAP_DEFAULT_ZOOM = MANGALURU_DEFAULT_ZOOM;

// Real-world key landmark coordinates for Coastal Karnataka
export interface RealLandmark {
  id: string;
  name: string;
  category: string;
  coordinates: [number, number]; // [lat, lon]
  description: string;
}

export const MANGALURU_LANDMARKS: RealLandmark[] = [
  {
    id: 'mng_hampankatta',
    name: 'Hampankatta (City Center)',
    category: 'Transit & Commercial Core',
    coordinates: [12.8703, 74.8427],
    description: 'Central hub near Mangaluru Central Railway Station & KS Rao Road',
  },
  {
    id: 'mng_kottara_chowki',
    name: 'Kottara Chowki Junction',
    category: 'Major Highway Intersection',
    coordinates: [12.9102, 74.8363],
    description: 'Northern junction connecting NH 66, Kuloor Ferry Road & Airport Corridor',
  },
  {
    id: 'mng_lalbagh',
    name: 'Lalbagh (MCC Headquarters)',
    category: 'Civic Center',
    coordinates: [12.8841, 74.8402],
    description: 'Mangaluru City Corporation & Ladyhill junction',
  },
  {
    id: 'mng_pumpwell',
    name: 'Pumpwell (Mahaveer Circle)',
    category: 'Southern Gateway',
    coordinates: [12.8569, 74.8698],
    description: 'Major arterial interchange connecting NH 66 (Kasaragod) & NH 73 (Bengaluru)',
  },
  {
    id: 'mng_surathkal',
    name: 'Surathkal (NITK Corridor)',
    category: 'Northern Coastal Hub',
    coordinates: [13.0119, 74.7943],
    description: 'National Highway 66 arterial connecting Udupi & Mangaluru industrial belt',
  },
  {
    id: 'mng_sdit_kenjar',
    name: 'SDIT Kenjar (Airport Road)',
    category: 'Educational & Airport Corridor',
    coordinates: [12.9610, 74.8967],
    description: 'Shree Devi Institute of Technology campus on Bajpe Airport Road',
  },
  {
    id: 'mng_airport',
    name: 'Mangaluru International Airport (IXE)',
    category: 'Aviation Terminal',
    coordinates: [12.9613, 74.8900],
    description: 'Bajpe international aviation terminal',
  },
];

export const TILE_PROVIDERS = {
  cartoVoyager: {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: ['a', 'b', 'c', 'd'],
    maxZoom: 19,
  },
  cartoDarkMatter: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: ['a', 'b', 'c', 'd'],
    maxZoom: 19,
  },
  osmStandard: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    subdomains: ['a', 'b', 'c'],
    maxZoom: 19,
  },
};


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
