const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

export interface LatLng {
  lat: number;
  lng: number;
}

export interface GeoLineString {
  type: "LineString";
  coordinates: [number, number][];
}

export interface ScenarioSummary {
  scenario_id: string;
  label: string;
  rainfall_intensity_mm_hr: number;
  duration_min: number;
}

export interface NodePrediction {
  node_id: string;
  lat: number;
  lng: number;
  depth_m_mean: number;
  depth_m_std: number;
}

export interface RoadSegment {
  edge_id: string;
  state: "clear" | "at_risk" | "flooded";
  geometry: GeoLineString;
}

export interface SimulateResponse {
  scenario_id: string;
  node_predictions: NodePrediction[];
  road_segments: RoadSegment[];
  model_caveat: string;
  is_synthetic_ward: boolean;
  // infra_ids with zero access redundancy under this scenario -- lets the
  // map's demo-click affordance target a facility that's actually
  // vulnerable right now, not just whichever infra happens to be first.
  at_risk_infra_ids: string[];
}

export interface CriticalAccessRisk {
  infra_id: string;
  infra_type: string;
  infra_name: string;
  access_redundancy_score: number;
  message: string;
}

export interface RouteResponse {
  route_geometry: GeoLineString;
  eta_seconds: number;
  avoided_flooded_segments: string[];
  baseline_route_geometry: GeoLineString;
  baseline_eta_seconds: number;
  critical_access_risk: CriticalAccessRisk | null;
}

export interface CriticalInfraItem {
  infra_id: string;
  infra_type: string;
  name: string;
  lat: number;
  lng: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}) as any);
    throw new Error(body.message || body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getScenarios: () => request<ScenarioSummary[]>("/api/scenarios"),
  getCriticalInfrastructure: () => request<CriticalInfraItem[]>("/api/critical-infrastructure"),
  simulate: (rainfall_intensity_mm_hr: number, duration_min: number) =>
    request<SimulateResponse>("/api/simulate", {
      method: "POST",
      body: JSON.stringify({ rainfall_intensity_mm_hr, duration_min }),
    }),
  route: (start: LatLng, end: LatLng, scenario_id: string, algorithm: "astar" | "dijkstra" = "astar") =>
    request<RouteResponse>("/api/route", {
      method: "POST",
      body: JSON.stringify({ start, end, scenario_id, algorithm }),
    }),
  liveSocketUrl: (scenario_id: string) =>
    `${BASE_URL.replace(/^http/, "ws")}/ws/live?scenario_id=${scenario_id}`,
  explain: (nodeId: string, rainfallIntensityMmHr: number, durationMin: number) =>
    request<{ node_id: string; factors: { factor: string; depth_delta_m: number }[] }>(
      `/api/explain/${nodeId}?rainfall_intensity_mm_hr=${rainfallIntensityMmHr}&duration_min=${durationMin}`,
    ),
};
