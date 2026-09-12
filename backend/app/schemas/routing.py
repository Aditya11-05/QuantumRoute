from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class OptimizationWeightsIn(BaseModel):
    travel_time: float = Field(0.35, ge=0)
    congestion: float = Field(0.30, ge=0)
    distance: float = Field(0.15, ge=0)
    fuel: float = Field(0.10, ge=0)
    intersection: float = Field(0.05, ge=0)
    incident: float = Field(0.05, ge=0)


class RouteRequest(BaseModel):
    source: Coordinate
    destination: Coordinate

    traffic_scenario: str = Field(
        "low",
        description=(
            "Demo mode only: low, medium, heavy, peak, "
            "incident, closure"
        ),
    )

    timestamp: Optional[datetime] = Field(
        None,
        description=(
            "Historical METR-LA timestamp used in research mode. "
            "Must fall within the available METR-LA period."
        ),
    )

    weights: Optional[OptimizationWeightsIn] = None


class RouteResponse(BaseModel):
    algorithm: str
    found: bool
    reason: Optional[str] = None

    node_path: List[int] = []
    coordinates: List[Tuple[float, float]] = []

    total_distance_m: float = 0.0
    total_travel_time_sec: float = 0.0
    total_cost: float = 0.0

    num_edges: int = 0
    computation_time_ms: float = 0.0

    graph_source: str
    region: str


class OptimizeRouteResponse(BaseModel):
    found: bool
    reason: Optional[str] = None

    selected_route: Optional[RouteResponse] = None
    candidate_routes: List[RouteResponse] = []
    selected_index: Optional[int] = None

    # Optimizer correctness / transparency
    feasible_selection: bool
    was_repaired: bool

    exact_optimal_index: Optional[int] = None
    exact_optimal_cost: Optional[float] = None
    selected_cost: Optional[float] = None
    optimality_gap_pct: Optional[float] = None
    matches_exact_optimum: Optional[bool] = None

    # QUBO / solver details
    qubo_size: int
    qubo_penalty: float

    solver_iterations: int
    solver_runtime_ms: float
    solver_best_energy: float
    solver_convergence_history: List[float] = []

    # Pipeline timings
    candidate_generation_time_ms: float
    qubo_build_time_ms: float
    total_pipeline_time_ms: float

    # Network provenance
    graph_source: str
    region: str

    # Traffic / research provenance
    mode: str
    traffic_provenance: str
    traffic_scenario: str
    timestamp: Optional[str] = None

    # Explicit quantum disclaimer
    quantum_disclaimer: str = (
        "This optimization is QUANTUM-INSPIRED (simulated annealing) "
        "and runs entirely on classical CPU hardware. No quantum "
        "computer or quantum circuit is used."
    )


class RegionInfo(BaseModel):
    name: str
    graph_source: str
    num_nodes: int
    num_edges: int
    bounding_box: dict
