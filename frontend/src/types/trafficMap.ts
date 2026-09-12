import type { AnalysisRequest } from "./api";

export type TrafficMapRequest = AnalysisRequest;

export interface TrafficMapSegment {
  u: number;
  v: number;
  key: number;
  coordinates: [number, number][];
  speed_kmh: number;
  congestion: number;
  highway: string;
  provenance: "REAL_HISTORICAL" | string;
}

export interface TrafficMapResponse {
  provenance: "REAL_HISTORICAL" | string;
  observed_edges: number;
  network_edges: number;
  coverage_pct: number;
  mean_speed_kmh: number | null;
  mean_congestion: number | null;
  segments: TrafficMapSegment[];
}
