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
  mode?: string;
  traffic_provenance?: string;
  timestamp?: string | null;
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

  // Research metadata; supported as the backend evolves.
  mode?: string;
  traffic_provenance?: string;
  timestamp?: string | null;
  exact_optimal_index?: number | null;
  sa_matches_exact?: boolean;
  route_cost_gap_pct?: number | null;
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

export interface AnalysisRequest {
  source: Coordinate;
  destination: Coordinate;
  traffic_scenario: string;
  timestamp?: string;
  weights: OptimizationWeights;
}

export type AnalysisRoute = RouteResponse;

export interface RouteAnalysisResponse {
  found: boolean;
  reason?: string | null;

  baseline: {
    dijkstra: AnalysisRoute | null;
    astar: AnalysisRoute | null;
  };

  optimization: {
    selected_route: AnalysisRoute | null;
    candidate_routes: AnalysisRoute[];
    selected_index: number | null;

    qubo_size: number;
    qubo_penalty: number;

    solver_iterations: number;
    solver_runtime_ms: number;
    solver_best_energy: number;
    solver_convergence_history: number[];

    was_repaired: boolean;
    feasible_selection?: boolean;

    candidate_generation_time_ms: number;
    qubo_build_time_ms: number;
    total_pipeline_time_ms: number;

    exact_optimal_index: number | null;
    exact_optimal_cost: number | null;
    selected_cost: number | null;
    optimality_gap_pct: number | null;
    matches_exact_optimum: boolean | null;
  };

  comparison: {
    distance_delta_m: number;
    travel_time_delta_sec: number;
    cost_delta: number;
    distance_change_pct: number | null;
    travel_time_change_pct: number | null;
    cost_change_pct: number | null;
  };

  snap: {
    source_distance_m: number;
    destination_distance_m: number;
  };

  traffic: {
    mode: string;
    traffic_provenance: string;
    traffic_scenario: string;
    timestamp: string | null;
  };

  network: {
    graph_source: string;
    region: string;
    num_nodes: number;
    num_edges: number;
  };

  weights: OptimizationWeights;

  interpretation: Record<string, string>;

  quantum_disclaimer: string;
}
