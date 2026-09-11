export interface Coordinate {
  lat: number;
  lon: number;
}

export interface OptimizationWeights {
  travel_time: number;
  congestion: number;
  distance: number;
  fuel: number;
  intersection: number;
  incident: number;
}

export type TrafficScenario =
  | "low"
  | "medium"
  | "heavy"
  | "peak"
  | "incident"
  | "closure";

export interface RouteResponse {
  algorithm: string;
  found: boolean;
  reason?: string | null;
  node_path: number[];
  coordinates: [number, number][];
  total_distance_m: number;
  total_travel_time_sec: number;
  total_cost: number;
  num_edges: number;
  computation_time_ms: number;
  graph_source: string;
  region: string;
}

export interface BaselineResponse {
  dijkstra: RouteResponse;
  astar: RouteResponse;
  source_snap_distance_m: number;
  destination_snap_distance_m: number;
  traffic_scenario: string;
}

export interface OptimizeRouteResponse {
  found: boolean;
  reason?: string | null;
  selected_route: RouteResponse | null;
  candidate_routes: RouteResponse[];
  selected_index: number | null;
  qubo_size: number;
  qubo_penalty: number;
  solver_iterations: number;
  solver_runtime_ms: number;
  solver_best_energy: number;
  solver_convergence_history: number[];
  was_repaired: boolean;
  candidate_generation_time_ms: number;
  qubo_build_time_ms: number;
  total_pipeline_time_ms: number;
  graph_source: string;
  region: string;
  quantum_disclaimer: string;
}

export interface TrafficSummary {
  scenario: string;
  seed: number;
  num_edges: number;
  avg_congestion: number;
  avg_speed_kmh: number;
  num_incidents: number;
  num_closures: number;
  is_synthetic: boolean;
  disclaimer: string;
}

export interface TrafficPredictResponse {
  predicted_speed_ratio: number;
  predicted_congestion_level: number;
  inference_time_ms: number;
  model_loaded: boolean;
  model_disclaimer: string;
}

export interface SystemStatus {
  app_name: string;
  app_version: string;
  project_mode: string;
  graph_source: string;
  region: string;
  num_nodes: number;
  num_edges: number;
  ml_model_loaded: boolean;
  ml_model_load_error: string | null;
  quantum_disclaimer: string;
}

export interface RegionInfo {
  name: string;
  graph_source: string;
  num_nodes: number;
  num_edges: number;
  bounding_box: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
}

export interface AlgorithmResult {
  algorithm: string;
  found: boolean;
  distance_m: number;
  travel_time_sec: number;
  congestion_avg?: number | null;
  total_cost: number;
  runtime_ms: number;
}

export interface ScenarioBenchmark {
  scenario: string;
  results: AlgorithmResult[];
}

export interface BenchmarkResponse {
  scenarios: ScenarioBenchmark[];
  graph_source: string;
  region: string;
  disclaimer: string;
}

export interface ModelInfo {
  trained: boolean;
  message?: string;
  model_type?: string;
  n_train?: number;
  n_test?: number;
  mae?: number;
  rmse?: number;
  r2?: number;
  training_time_sec?: number;
  feature_importances?: Record<string, number>;
}
