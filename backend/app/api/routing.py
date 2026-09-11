from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.optimization.optimizer import run_optimization
from app.routing.baseline import astar_route, dijkstra_route, RouteResult
from app.routing.cost import CostWeights
from app.routing.node_utils import nearest_node
from app.schemas.routing import OptimizeRouteResponse, RouteRequest, RouteResponse
from app.simulation.traffic import TrafficScenario, simulate_traffic
from app.state import get_graph_state

router = APIRouter(tags=["routing"])


def _weights_from_request(w) -> CostWeights:
    if w is None:
        settings = get_settings()
        return CostWeights(**settings.default_weights)
    return CostWeights(
        travel_time=w.travel_time, congestion=w.congestion, distance=w.distance,
        fuel=w.fuel, intersection=w.intersection, incident=w.incident,
    ).normalized()


def _validate_scenario(scenario: str) -> TrafficScenario:
    try:
        return TrafficScenario(scenario.lower())
    except ValueError:
        valid = ", ".join(s.value for s in TrafficScenario)
        raise HTTPException(status_code=400, detail=f"Invalid traffic_scenario '{scenario}'. Valid options: {valid}")


def _route_result_to_response(r: RouteResult, graph_source: str, region: str) -> RouteResponse:
    return RouteResponse(
        algorithm=r.algorithm, found=r.found, reason=r.reason,
        node_path=r.node_path, coordinates=r.coordinates,
        total_distance_m=r.total_distance_m, total_travel_time_sec=r.total_travel_time_sec,
        total_cost=r.total_cost, num_edges=r.num_edges,
        computation_time_ms=r.computation_time_ms,
        graph_source=graph_source, region=region,
    )


@router.post("/route/baseline")
def route_baseline(req: RouteRequest):
    lg = get_graph_state()
    G = lg.graph
    scenario = _validate_scenario(req.traffic_scenario)
    weights = _weights_from_request(req.weights)

    try:
        src_node, src_dist = nearest_node(G, req.source.lat, req.source.lon)
        dst_node, dst_dist = nearest_node(G, req.destination.lat, req.destination.lon)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    snapshot = simulate_traffic(G, scenario, seed=42)

    dijkstra = dijkstra_route(G, src_node, dst_node, snapshot, weights)
    astar = astar_route(G, src_node, dst_node, snapshot, weights)

    return {
        "dijkstra": _route_result_to_response(dijkstra, lg.source, lg.region),
        "astar": _route_result_to_response(astar, lg.source, lg.region),
        "source_snap_distance_m": round(src_dist, 1),
        "destination_snap_distance_m": round(dst_dist, 1),
        "traffic_scenario": scenario.value,
    }


@router.post("/route/optimize", response_model=OptimizeRouteResponse)
def route_optimize(req: RouteRequest):
    lg = get_graph_state()
    G = lg.graph
    scenario = _validate_scenario(req.traffic_scenario)
    weights = _weights_from_request(req.weights)
    settings = get_settings()

    try:
        src_node, _ = nearest_node(G, req.source.lat, req.source.lon)
        dst_node, _ = nearest_node(G, req.destination.lat, req.destination.lon)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    snapshot = simulate_traffic(G, scenario, seed=42)

    result = run_optimization(
        G, src_node, dst_node, snapshot, weights,
        k_candidates=5, iterations=settings.OPTIMIZATION_ITERATIONS,
    )

    if not result.found:
        return OptimizeRouteResponse(
            found=False, reason=result.reason,
            qubo_size=0, qubo_penalty=0.0, solver_iterations=0,
            solver_runtime_ms=0.0, solver_best_energy=0.0,
            was_repaired=False, candidate_generation_time_ms=result.candidate_generation_time_ms,
            qubo_build_time_ms=0.0, total_pipeline_time_ms=result.total_pipeline_time_ms,
            graph_source=lg.source, region=lg.region,
        )

    return OptimizeRouteResponse(
        found=True,
        selected_route=_route_result_to_response(result.selected_route, lg.source, lg.region),
        candidate_routes=[_route_result_to_response(r, lg.source, lg.region) for r in result.candidate_routes],
        selected_index=result.selected_index,
        qubo_size=result.qubo_size,
        qubo_penalty=result.qubo_penalty,
        solver_iterations=result.solver.iterations,
        solver_runtime_ms=result.solver.runtime_ms,
        solver_best_energy=result.solver.best_energy,
        solver_convergence_history=result.solver.convergence_history,
        was_repaired=result.was_repaired,
        candidate_generation_time_ms=result.candidate_generation_time_ms,
        qubo_build_time_ms=result.qubo_build_time_ms,
        total_pipeline_time_ms=result.total_pipeline_time_ms,
        graph_source=lg.source,
        region=lg.region,
    )
