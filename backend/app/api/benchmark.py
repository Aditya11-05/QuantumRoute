from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.benchmarking.benchmark import run_benchmark
from app.routing.node_utils import nearest_node
from app.schemas.benchmark import AlgorithmResult, BenchmarkRequest, BenchmarkResponse, ScenarioBenchmark
from app.state import get_graph_state

router = APIRouter(tags=["benchmark"])


@router.post("/benchmark", response_model=BenchmarkResponse)
def benchmark(req: BenchmarkRequest):
    lg = get_graph_state()
    G = lg.graph
    try:
        src_node, _ = nearest_node(G, req.source["lat"], req.source["lon"])
        dst_node, _ = nearest_node(G, req.destination["lat"], req.destination["lon"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid source/destination: {exc}")

    scenario_results = run_benchmark(
        G, src_node, dst_node, scenarios=req.scenarios, seed=req.seed,
        k_candidates=req.k_candidates, iterations=req.iterations,
    )

    return BenchmarkResponse(
        scenarios=[
            ScenarioBenchmark(
                scenario=sr.scenario,
                results=[
                    AlgorithmResult(
                        algorithm=r.algorithm, found=r.found, distance_m=r.distance_m,
                        travel_time_sec=r.travel_time_sec, total_cost=r.total_cost,
                        runtime_ms=r.runtime_ms,
                    ) for r in sr.results
                ],
            ) for sr in scenario_results
        ],
        graph_source=lg.source,
        region=lg.region,
    )
