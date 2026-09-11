import type {
  BaselineResponse,
  BenchmarkResponse,
  Coordinate,
  ModelInfo,
  OptimizationWeights,
  OptimizeRouteResponse,
  RegionInfo,
  SystemStatus,
  TrafficPredictResponse,
  TrafficSummary,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${options?.method ?? "GET"} ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

export function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>("/system/status");
}

export function getRegions(): Promise<RegionInfo[]> {
  return request<RegionInfo[]>("/map/regions");
}

export function getBaselineRoute(
  source: Coordinate,
  destination: Coordinate,
  trafficScenario: string,
  weights?: OptimizationWeights,
): Promise<BaselineResponse> {
  return request<BaselineResponse>("/route/baseline", {
    method: "POST",
    body: JSON.stringify({ source, destination, traffic_scenario: trafficScenario, weights }),
  });
}

export function optimizeRoute(
  source: Coordinate,
  destination: Coordinate,
  trafficScenario: string,
  weights?: OptimizationWeights,
): Promise<OptimizeRouteResponse> {
  return request<OptimizeRouteResponse>("/route/optimize", {
    method: "POST",
    body: JSON.stringify({ source, destination, traffic_scenario: trafficScenario, weights }),
  });
}

export function simulateTraffic(scenario: string, seed = 42): Promise<TrafficSummary> {
  return request<TrafficSummary>("/traffic/simulate", {
    method: "POST",
    body: JSON.stringify({ scenario, seed }),
  });
}

export function predictCongestion(params: {
  hour: number;
  day_of_week: number;
  road_type: string;
  occupancy: number;
}): Promise<TrafficPredictResponse> {
  return request<TrafficPredictResponse>("/traffic/predict", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getModelInfo(): Promise<ModelInfo> {
  return request<ModelInfo>("/model/info");
}

export function runBenchmark(
  source: Coordinate,
  destination: Coordinate,
  scenarios?: string[],
): Promise<BenchmarkResponse> {
  return request<BenchmarkResponse>("/benchmark", {
    method: "POST",
    body: JSON.stringify({ source, destination, scenarios }),
  });
}
