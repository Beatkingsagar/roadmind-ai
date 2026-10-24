/**
 * RoadMind AI — Core TypeScript interfaces matching backend Pydantic schemas.
 */

export type DataMode = 'synthetic' | 'historical' | 'user_submitted';

export type IncidentType = 'accident' | 'pothole' | 'road_damage' | 'debris' | 'flooding' | 'stall';

export type ReviewDecision = 'verified' | 'rejected' | 'needs_investigation';

export type SensitivityOutcome =
  | 'ROBUST_ALTERNATIVE'
  | 'EVIDENCE_SENSITIVE'
  | 'NO_ROUTE_AVAILABLE'
  | 'INSUFFICIENT_DATA';

export type AbstentionReason =
  | 'INSUFFICIENT_HISTORY'
  | 'STALE_OBSERVATIONS'
  | 'UNOBSERVED_SEGMENT'
  | 'INVALID_UNITS';

// Health Check
export interface HealthStatus {
  status: 'healthy' | 'degraded';
  version: string;
  app_name: string;
  database: string;
  environment: string;
  graph_version: string;
}

// GeoJSON & Road Network
export interface GeoJSONGeometry {
  type: string;
  coordinates: [number, number][]; // [lon, lat]
}

export interface RoadSegmentProperties {
  id: string;
  name: string;
  source_node: string;
  target_node: string;
  directed_edge_id: string;
  is_one_way: boolean;
  length_meters: number;
  free_flow_speed_mps: number;
  free_flow_speed_kmph: number;
  functional_class: string;
  access_assumptions: string;
  data_mode: DataMode;
}

export interface GeoJSONFeature {
  type: 'Feature';
  id: string;
  geometry: GeoJSONGeometry;
  properties: RoadSegmentProperties;
}

export interface NetworkGeoJSONResponse {
  type: 'FeatureCollection';
  graph_version: string;
  data_mode: DataMode;
  attribution: string;
  features: GeoJSONFeature[];
}

export interface RoadSegmentResponse extends RoadSegmentProperties {
  free_flow_travel_time_seconds: number;
  coordinates: [number, number][];
}

export interface RoadStateSnapshot {
  segment_id: string;
  name: string;
  source_node: string;
  target_node: string;
  current_speed_mps: number;
  current_speed_kmph: number;
  free_flow_speed_mps: number;
  congestion_ratio: number;
  active_incidents_count: number;
  latest_observation_time: string | null;
  observation_freshness_seconds: number | null;
  provenance: string;
  data_mode: DataMode;
}

// Reports & Evidence
export interface ReportCreate {
  incident_type: IncidentType;
  claimed_event_time: string;
  segment_id: string;
  location_description: string;
  latitude: number;
  longitude: number;
  reporter_reference: string;
  dependency_group_id?: string;
  description: string;
  idempotency_key?: string;
}

export interface EvidenceResponse {
  id: string;
  report_id: string;
  content_hash: string;
  media_type: string;
  file_size_bytes: number;
  metadata_claims: Record<string, unknown>;
  is_duplicate: boolean;
  duplicate_of_id: string | null;
  perceptual_hash: string | null;
  submitted_at: string;
  available_at: string;
}

export interface ReportResponse {
  id: string;
  incident_type: string;
  claimed_event_time: string;
  submitted_at: string;
  available_at: string;
  segment_id: string;
  location_description: string;
  latitude: number;
  longitude: number;
  reporter_reference: string;
  dependency_group_id?: string | null;
  description: string;
  data_mode: DataMode;
  idempotency_key?: string | null;
  episode_id?: string | null;
  evidence_items: EvidenceResponse[];
}

// Incidents & Reviews
export interface IncidentEpisodeResponse {
  id: string;
  primary_segment_id: string;
  affected_segments: string[];
  episode_type: string;
  first_reported_at: string;
  last_reported_at: string;
  lifecycle_status: string;
  severity_level: string;
  heuristic_support_score: number;
  assessment_summary: string;
  rubric_version: string;
  reviewer_state: string;
  report_count: number;
}

export interface IncidentReviewResponse {
  id: string;
  episode_id: string;
  reviewer_reference: string;
  decision: string;
  reason: string;
  previous_state: string;
  recorded_at: string;
  available_at: string;
}

export interface IncidentEpisodeDetailResponse extends IncidentEpisodeResponse {
  reports: ReportResponse[];
  reviews: IncidentReviewResponse[];
}

export interface IncidentReviewCreate {
  reviewer_reference: string;
  decision: ReviewDecision;
  reason: string;
}

// Forecasting & Evaluation
export interface PredictionResponse {
  id: string;
  segment_id: string;
  issue_time: string;
  target_time: string;
  horizon_minutes: number;
  model_version: string;
  input_snapshot_reference: string;
  predicted_speed_mps: number | null;
  predicted_speed_kmph: number | null;
  interval_lower_mps: number | null;
  interval_upper_mps: number | null;
  confidence_level: number;
  abstention_reason: AbstentionReason | null;
  is_abstained: boolean;
  data_mode: DataMode;
}

export interface EvaluationSummary {
  horizon_minutes: number;
  sample_count: number;
  mae_mps: number;
  rmse_mps: number;
  interval_coverage_pct: number;
  dataset_scope: string;
  evaluation_version: string;
}

export interface OutcomeEvaluationResponse {
  id: string;
  prediction_id: string;
  observation_id: string;
  error_speed_mps: number;
  absolute_error_mps: number;
  within_interval: boolean;
  evaluated_at: string;
  evaluation_version: string;
}

export interface EvaluationsData {
  evaluation_time: string;
  tolerance_minutes: number;
  sample_metrics: {
    total_predictions: number;
    evaluated_count: number;
    abstained_count: number;
    missing_actual_count: number;
  };
  horizon_summaries: Record<string, EvaluationSummary>;
  evaluations: OutcomeEvaluationResponse[];
}

// Simulation & Routing
export interface ScenarioOverride {
  closed?: boolean;
  speed_mps?: number | null;
  delay_seconds?: number;
}

export interface SimulationRequest {
  origin_node: string;
  destination_node: string;
  incident_segment_id?: string;
  overrides?: Record<string, ScenarioOverride>;
  minimum_benefit_seconds?: number;
}

export interface RouteAlternative {
  route_name: string;
  edge_ids: string[];
  nodes: string[];
  total_length_meters: number;
  estimated_travel_time_seconds: number;
  is_reachable: boolean;
  assumptions_applied: string;
}

export interface ScenarioEvaluation {
  scenario_type: string;
  reference_route?: RouteAlternative | null;
  candidate_routes: RouteAlternative[];
  preferred_route_name?: string | null;
  time_saved_seconds: number;
}

export interface RecommendationResponse {
  id: string;
  simulation_run_id: string;
  decision_rule_version: string;
  explanation: string;
  sensitivity_outcome: SensitivityOutcome;
  minimum_benefit_seconds: number;
  created_at: string;
}

export interface SimulationRunResponse {
  id: string;
  created_at: string;
  baseline_snapshot_time: string;
  graph_version: string;
  scenario_type: string;
  recommendation?: RecommendationResponse | null;
  scenarios: Record<string, ScenarioEvaluation>;
  sensitivity_summary: string;
}

// Road Memory & Inspection Priority
export interface ObservationCoverage {
  segment_id: string;
  observation_count: number;
  first_observation_time: string | null;
  latest_observation_time: string | null;
  coverage_span_hours: number;
  is_coverage_poor: boolean;
  coverage_limitation_note: string | null;
}

export interface EpisodeCluster {
  id: string;
  segment_id: string;
  episode_type: string;
  first_reported_at: string;
  last_reported_at: string;
  duration_minutes: number;
  severity_level: string;
  report_count: number;
  report_ids: string[];
  unique_source_count: number;
  dependency_group_ids: string[];
}

export interface SegmentMemorySummary {
  segment_id: string;
  segment_name: string;
  observed_recurrence_count: number;
  total_report_count: number;
  duplicate_or_shared_reports_count: number;
  average_episode_duration_minutes: number;
  max_severity: string;
  episodes: EpisodeCluster[];
  observation_coverage: ObservationCoverage;
}

export interface InspectionPriority {
  segment_id: string;
  segment_name: string;
  priority_score: number;
  priority_rank: number;
  observed_recurrence_score: number;
  severity_score: number;
  duration_score: number;
  coverage_uncertainty_score: number;
  scoring_rubric_version: string;
  explanation: string;
  data_limitations: string[];
}

export interface SegmentHistoryResponse {
  segment: RoadSegmentResponse;
  replay_time: string;
  total_observations_eligible: number;
  total_reports_eligible: number;
  memory_summary: SegmentMemorySummary | null;
  recent_observations: Array<{
    id: string;
    segment_id: string;
    observed_at: string;
    available_at: string;
    speed_mps: number;
    speed_kmph: number;
    unit: string;
    quality_score: number;
    provenance: string;
  }>;
}

// Real-World Map Geocoding and Place Search
export interface PlaceSearchResult {
  id: string;
  display_name: string;
  name: string;
  category?: string;
  type?: string;
  lat: number;
  lon: number;
  bounding_box?: number[];
  source: 'verified_cache' | 'osm_nominatim' | string;
  importance?: number;
  raw_address?: Record<string, unknown>;
}

export interface PlaceSearchResponse {
  query: string;
  count: number;
  results: PlaceSearchResult[];
  source: string;
  attribution: string;
}

export interface RealPlace {
  id: string;
  name: string;
  displayName: string;
  lat: number;
  lon: number;
  source: string;
  category?: string;
}

// Real-World Road Routing (Phase 3)
export interface RealRouteWaypoint {
  name: string;
  lat: number;
  lon: number;
  distance_to_snapped_meters?: number;
}

export interface RealRouteLeg {
  summary: string;
  distance_meters: number;
  duration_seconds: number;
}

export interface RealRoadRoute {
  route_index: number;
  is_primary: boolean;
  summary: string;
  distance_meters: number;
  distance_km: number;
  duration_seconds: number;
  duration_minutes: number;
  geometry: {
    type: string;
    coordinates: [number, number][]; // [lon, lat]
  };
  legs: RealRouteLeg[];
  weight_name: string;
}

export interface RealRouteRequest {
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  origin_name?: string;
  destination_name?: string;
  alternatives?: boolean;
}

export interface RealRouteResponse {
  origin: RealRouteWaypoint;
  destination: RealRouteWaypoint;
  primary_route: RealRoadRoute;
  alternative_routes: RealRoadRoute[];
  provider: string;
  profile: string;
  traffic_model: string;
  attribution: string;
}

// ============================================================================
// Journey Budget, Fuel Cost, and Toll Estimation (Phase 5)
// ============================================================================

export type VehicleType = 'motorcycle' | 'car' | 'suv' | 'custom';
export type FuelType = 'petrol' | 'diesel' | 'cng' | 'ev' | 'other';
export type TollStatus = 'available' | 'unavailable' | 'disabled' | 'error';

export interface TollPlazaInfo {
  plaza_name: string;
  road_name?: string;
  cost: number;
  currency: string;
  payment_method: string;
  is_confirmed: boolean;
  latitude?: number;
  longitude?: number;
}

export interface TollEstimate {
  status: TollStatus;
  provider: string;
  total_toll: number | null;
  currency: string;
  plazas: TollPlazaInfo[];
  is_confirmed: boolean;
  is_estimated: boolean;
  source: string;
  message: string;
}

export interface FuelCostEstimate {
  fuel_required_units: number;
  fuel_unit: string;
  fuel_price_per_unit: number;
  fuel_efficiency_km_per_unit: number;
  one_way_fuel_cost: number;
  return_trip_fuel_cost: number;
  active_fuel_cost: number;
  is_round_trip: boolean;
}

export interface JourneyBudgetRequest {
  distance_km: number;
  vehicle_type: VehicleType;
  custom_vehicle_name?: string;
  fuel_type: FuelType;
  fuel_efficiency_km_per_unit: number;
  fuel_price_per_unit: number;
  is_round_trip?: boolean;
  encoded_polyline?: string;
  route_geometry?: Record<string, unknown>;
  origin_name?: string;
  destination_name?: string;
}

export interface JourneyBudgetResponse {
  distance_km: number;
  effective_distance_km: number;
  is_round_trip: boolean;
  vehicle_type: string;
  vehicle_label: string;
  fuel_type: string;
  fuel_cost: FuelCostEstimate;
  toll: TollEstimate;
  estimated_total_cost: number;
  total_includes_toll: boolean;
  currency: string;
  assumptions: string[];
}

export interface TollStatusResponse {
  active_provider: string;
  is_configured: boolean;
  is_available: boolean;
  message: string;
  supported_regions: string[];
}

