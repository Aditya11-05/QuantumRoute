from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BenchmarkRequest(BaseModel):
    source: dict  # {"lat":..,"lon":..}
    destination: dict
    scenarios: Optional[List[str]] = None  # defaults to all 6 scenarios
    seed: int = 42
    k_candidates: int = 5
    iterations: int = 2000


class AlgorithmResult(BaseModel):
    algorithm: str
    found: bool
    distance_m: float
    travel_time_sec: float
    congestion_avg: Optional[float] = None
    total_cost: float
    runtime_ms: float


class ScenarioBenchmark(BaseModel):
    scenario: str
    results: List[AlgorithmResult]


class BenchmarkResponse(BaseModel):
    scenarios: List[ScenarioBenchmark]
    graph_source: str
    region: str
    disclaimer: str = (
        "All values below come from actually running each algorithm on this "
        "request's source/destination under the synthetic traffic simulator "
        "for each scenario. QuantumRoute is not guaranteed to win every "
        "scenario; see docs/benchmarking.md for methodology."
    )
