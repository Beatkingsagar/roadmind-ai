/**
 * RoadMind AI — Typed API Client.
 * Communicates with the FastAPI backend under /api/v1 and /api/health.
 */

import type {
  EvaluationsData,
  EvidenceResponse,
  HealthStatus,
  IncidentEpisodeDetailResponse,
  IncidentEpisodeResponse,
  IncidentReviewCreate,
  IncidentReviewResponse,
  InspectionPriority,
  NetworkGeoJSONResponse,
  PredictionResponse,
  ReportCreate,
  ReportResponse,
  RoadSegmentResponse,
  RoadStateSnapshot,
  SegmentHistoryResponse,
  SimulationRequest,
  SimulationRunResponse,
  PlaceSearchResponse,
  RealRouteRequest,
  RealRouteResponse,
  JourneyBudgetRequest,
  JourneyBudgetResponse,
  TollEstimate,
  TollStatusResponse,
} from './types';


export const DEFAULT_API_BASE = 'http://127.0.0.1:8000';
export const DEFAULT_OPERATOR_TOKEN = 'traffic_operator_secret_2026';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

class RoadMindApiClient {
  private getBaseUrl(): string {
    const customUrl = localStorage.getItem('roadmind_api_url');
    return customUrl?.trim() || import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE;
  }

  private getOperatorToken(): string {
    const customToken = localStorage.getItem('roadmind_operator_token');
    return customToken?.trim() || DEFAULT_OPERATOR_TOKEN;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const baseUrl = this.getBaseUrl();
    const url = `${baseUrl}${endpoint}`;

    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errMessage = `HTTP ${response.status}: ${response.statusText}`;
        let errorData: unknown;
        try {
          errorData = await response.json();
          if (typeof errorData === 'object' && errorData !== null) {
            const errObj = errorData as Record<string, unknown>;
            if (errObj.error && typeof errObj.error === 'object') {
              const inner = errObj.error as Record<string, unknown>;
              errMessage = (inner.message as string) || errMessage;
            } else if (errObj.detail) {
              errMessage = (errObj.detail as string) || errMessage;
            }
          }
        } catch {
          // Response body was not JSON
        }
        throw new ApiError(response.status, errMessage, errorData);
      }

      return (await response.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(
        0,
        `Network or connection error reaching backend at ${baseUrl}. Please ensure backend is running.`,
        err
      );
    }
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health');
  }

  // Network & Road State
  async getNetwork(): Promise<NetworkGeoJSONResponse> {
    return this.request<NetworkGeoJSONResponse>('/api/v1/network');
  }

  async getSegments(): Promise<RoadSegmentResponse[]> {
    return this.request<RoadSegmentResponse[]>('/api/v1/network/segments');
  }

  async getRoadState(at?: string): Promise<RoadStateSnapshot[]> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<RoadStateSnapshot[]>(`/api/v1/road-state${qs}`);
  }

  async getSegmentHistory(segmentId: string, at?: string): Promise<SegmentHistoryResponse> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<SegmentHistoryResponse>(`/api/v1/segments/${segmentId}/history${qs}`);
  }

  // Reports & Evidence
  async createReport(data: ReportCreate): Promise<ReportResponse> {
    return this.request<ReportResponse>('/api/v1/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async uploadEvidence(
    reportId: string,
    file: File,
    metadataClaims?: Record<string, unknown>
  ): Promise<EvidenceResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadataClaims) {
      formData.append('metadata_claims', JSON.stringify(metadataClaims));
    }

    const baseUrl = this.getBaseUrl();
    const url = `${baseUrl}/api/v1/reports/${reportId}/evidence`;

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errMessage = `HTTP ${response.status}: Evidence upload failed`;
      try {
        const errorData = await response.json();
        errMessage = errorData.detail || errMessage;
      } catch {
        // ignore
      }
      throw new ApiError(response.status, errMessage);
    }

    return (await response.json()) as EvidenceResponse;
  }

  // Incidents & Reviews
  async getIncidents(at?: string, segmentId?: string, status?: string): Promise<IncidentEpisodeResponse[]> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    if (segmentId) params.append('segment_id', segmentId);
    if (status) params.append('lifecycle_status', status);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<IncidentEpisodeResponse[]>(`/api/v1/incidents${qs}`);
  }

  async getIncidentDetail(id: string, at?: string): Promise<IncidentEpisodeDetailResponse> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<IncidentEpisodeDetailResponse>(`/api/v1/incidents/${id}${qs}`);
  }

  async submitReview(
    episodeId: string,
    review: IncidentReviewCreate,
    operatorRole: string = 'traffic_operator'
  ): Promise<IncidentReviewResponse> {
    const token = this.getOperatorToken();
    return this.request<IncidentReviewResponse>(`/api/v1/incidents/${episodeId}/reviews`, {
      method: 'POST',
      headers: {
        'X-Reviewer-Role': operatorRole,
        'X-Reviewer-Token': token,
      },
      body: JSON.stringify(review),
    });
  }

  // Forecasting & Evaluations
  async getForecast(
    segmentId: string,
    at?: string,
    horizonMinutes: number = 15,
    modelType: 'persistence' | 'historical_median' = 'persistence',
    persist: boolean = false
  ): Promise<PredictionResponse> {
    const params = new URLSearchParams();
    params.append('segment_id', segmentId);
    if (at) params.append('at', at);
    params.append('horizon_minutes', horizonMinutes.toString());
    params.append('model_type', modelType);
    if (persist) params.append('persist', 'true');
    return this.request<PredictionResponse>(`/api/v1/forecasts?${params.toString()}`);
  }

  async getEvaluations(
    at?: string,
    horizonMinutes?: number,
    toleranceMinutes: number = 5
  ): Promise<EvaluationsData> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    if (horizonMinutes) params.append('horizon_minutes', horizonMinutes.toString());
    params.append('tolerance_minutes', toleranceMinutes.toString());
    return this.request<EvaluationsData>(`/api/v1/evaluations?${params.toString()}`);
  }

  // Simulations & Scenario Routing
  async createSimulation(req: SimulationRequest): Promise<SimulationRunResponse> {
    return this.request<SimulationRunResponse>('/api/v1/simulations', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async getSimulation(id: string): Promise<SimulationRunResponse> {
    return this.request<SimulationRunResponse>(`/api/v1/simulations/${id}`);
  }

  async compareScenarios(req: SimulationRequest): Promise<SimulationRunResponse> {
    return this.request<SimulationRunResponse>('/api/v1/simulations/compare', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  // Road Memory & Inspection Priority
  async getInspectionPriorities(at?: string): Promise<InspectionPriority[]> {
    const params = new URLSearchParams();
    if (at) params.append('at', at);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<InspectionPriority[]>(`/api/v1/memory/priority${qs}`);
  }

  // Admin
  async seedDatabase(reset: boolean = false): Promise<{ status: string; counts: Record<string, number> }> {
    const token = this.getOperatorToken();
    return this.request<{ status: string; counts: Record<string, number> }>(
      `/api/v1/admin/seed?reset=${reset}`,
      {
        method: 'POST',
        headers: {
          'X-Reviewer-Role': 'admin',
          'X-Reviewer-Token': token,
        },
      }
    );
  }

  // Real-World Map Geocoding
  async searchPlaces(query: string, limit: number = 5, bypassCache: boolean = false): Promise<PlaceSearchResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    if (limit) params.append('limit', limit.toString());
    if (bypassCache) params.append('bypass_cache', 'true');
    return this.request<PlaceSearchResponse>(`/api/v1/real-map/search?${params.toString()}`);
  }

  // Real-World Road Routing (Phase 3)
  async calculateRealRoute(req: RealRouteRequest, bypassCache: boolean = false): Promise<RealRouteResponse> {
    const qs = bypassCache ? '?bypass_cache=true' : '';
    return this.request<RealRouteResponse>(`/api/v1/real-map/route${qs}`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  // Journey Budget, Fuel Cost, and Tolls (Phase 5)
  async calculateJourneyBudget(req: JourneyBudgetRequest): Promise<JourneyBudgetResponse> {
    return this.request<JourneyBudgetResponse>('/api/v1/real-map/budget', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async estimateRouteToll(req: {
    route_distance_km?: number;
    encoded_polyline?: string;
    route_geometry?: Record<string, unknown>;
    vehicle_type?: string;
    is_round_trip?: boolean;
  }): Promise<TollEstimate> {
    return this.request<TollEstimate>('/api/v1/real-map/toll', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  async getTollStatus(): Promise<TollStatusResponse> {
    return this.request<TollStatusResponse>('/api/v1/real-map/toll/status');
  }
}

export const api = new RoadMindApiClient();

