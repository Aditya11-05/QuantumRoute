from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.data.real_traffic import (
    RealTrafficError,
    build_real_traffic_snapshot,
    load_metr_la,
)
from app.data.research_loader import (
    load_research_reference_speeds,
    load_sensor_edge_mappings,
    validate_research_data,
)
from app.optimization.optimizer import run_optimization
from app.routing.baseline import (
    RouteResult,
    astar_route,
    dijkstra_route,
)
from app.routing.cost import CostWeights
from app.routing.node_utils import nearest_node
from app.schemas.routing import (
    OptimizeRouteResponse,
    RouteRequest,
    RouteResponse,
)
from app.simulation.traffic import TrafficScenario, simulate_traffic
from app.state import get_graph_state


router = APIRouter(tags=["routing"])


def _weights_from_request(w) -> CostWeights:
    """
    Convert API optimization weights into the internal CostWeights object.

    Request-provided weights are normalized so they form a valid weighted
    objective. Configured default weights are already treated as the
    project's documented defaults.
    """
    if w is None:
        settings = get_settings()
        return CostWeights(**settings.default_weights)

    return CostWeights(
        travel_time=w.travel_time,
        congestion=w.congestion,
        distance=w.distance,
        fuel=w.fuel,
        intersection=w.intersection,
        incident=w.incident,
    ).normalized()


def _validate_scenario(scenario: str) -> TrafficScenario:
    """
    Validate the synthetic traffic scenario used only in demo mode.
    """
    try:
        return TrafficScenario(scenario.lower())
    except ValueError:
        valid = ", ".join(s.value for s in TrafficScenario)

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid traffic_scenario '{scenario}'. "
                f"Valid options: {valid}"
            ),
        )


def _route_result_to_response(
    r: RouteResult,
    graph_source: str,
    region: str,
) -> RouteResponse:
    """
    Convert the internal routing result into the public API schema.
    """
    return RouteResponse(
        algorithm=r.algorithm,
        found=r.found,
        reason=r.reason,
        node_path=r.node_path,
        coordinates=r.coordinates,
        total_distance_m=r.total_distance_m,
        total_travel_time_sec=r.total_travel_time_sec,
        total_cost=r.total_cost,
        num_edges=r.num_edges,
        computation_time_ms=r.computation_time_ms,
        graph_source=graph_source,
        region=region,
    )


def _validate_research_timestamp(req: RouteRequest) -> datetime:
    """
    Validate the historical METR-LA timestamp used in research mode.

    METR-LA is sampled at five-minute intervals.
    """
    if req.timestamp is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "timestamp is required when PROJECT_MODE=research. "
                "Provide a historical METR-LA timestamp."
            ),
        )

    # METR-LA is sampled every 5 minutes.
    timestamp = req.timestamp.replace(
        second=0,
        microsecond=0,
    )

    if timestamp.minute % 5 != 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Research timestamp must align to the METR-LA "
                "5-minute sampling interval."
            ),
        )

    return timestamp


def _build_traffic_snapshot(req: RouteRequest):
    """
    Build the traffic snapshot according to the configured project mode.

    DEMO:
        Synthetic traffic is allowed.

    RESEARCH:
        Only real historical METR-LA traffic is allowed.
        Missing research artifacts or invalid timestamps fail closed.

    Returns:
        (traffic_snapshot, traffic_metadata)
    """
    settings = get_settings()
    mode = settings.PROJECT_MODE.lower()

    # ---------------------------------------------------------
    # DEMO MODE
    # ---------------------------------------------------------
    if mode == "demo":
        scenario = _validate_scenario(req.traffic_scenario)

        snapshot = simulate_traffic(
            get_graph_state().graph,
            scenario,
            seed=42,
        )

        return snapshot, {
            "mode": "demo",
            "traffic_provenance": "SYNTHETIC",
            "traffic_scenario": scenario.value,
            "timestamp": None,
        }

    # ---------------------------------------------------------
    # RESEARCH MODE
    # ---------------------------------------------------------
    if mode == "research":
        timestamp = _validate_research_timestamp(req)

        traffic_path = settings.resolved_path(
            settings.RESEARCH_TRAFFIC_PATH
        )

        mapping_path = settings.resolved_path(
            settings.RESEARCH_SENSOR_MAPPING_PATH
        )

        reference_path = settings.resolved_path(
            settings.RESEARCH_REFERENCE_SPEED_PATH
        )

        try:
            # Fail closed if any required research artifact is missing
            # or structurally invalid.
            validate_research_data(
                traffic_path,
                mapping_path,
                reference_path,
            )

            # Load the actual historical METR-LA observation.
            sensor_row = load_metr_la(
                traffic_path,
                timestamp,
            )

            # Load the verified sensor -> OSM edge mapping.
            sensor_mappings = load_sensor_edge_mappings(
                mapping_path
            )

            # Load reference speeds derived from the research data /
            # verified OSM attributes.
            reference_speeds = load_research_reference_speeds(
                reference_path
            )

            # Build the traffic snapshot without synthetic traffic.
            snapshot = build_real_traffic_snapshot(
                get_graph_state().graph,
                sensor_row,
                sensor_mappings,
                reference_speeds,
            )

        except (
            RealTrafficError,
            FileNotFoundError,
            ValueError,
        ) as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Research traffic could not be loaded: {exc}"
                ),
            ) from exc

        return snapshot, {
            "mode": "research",
            "traffic_provenance": "REAL_HISTORICAL",
            "traffic_scenario": "real_historical",
            "timestamp": timestamp.isoformat(),
        }

    # ---------------------------------------------------------
    # INVALID MODE
    # ---------------------------------------------------------
    raise HTTPException(
        status_code=500,
        detail=(
            f"Unsupported PROJECT_MODE '{settings.PROJECT_MODE}'. "
            "Expected 'demo' or 'research'."
        ),
    )


@router.post("/route/baseline")
def route_baseline(req: RouteRequest):
    """
    Calculate classical baseline routes using the same traffic snapshot
    that would be used by the optimizer.
    """
    lg = get_graph_state()
    G = lg.graph

    weights = _weights_from_request(req.weights)

    try:
        src_node, src_dist = nearest_node(
            G,
            req.source.lat,
            req.source.lon,
        )

        dst_node, dst_dist = nearest_node(
            G,
            req.destination.lat,
            req.destination.lon,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    snapshot, traffic_meta = _build_traffic_snapshot(req)

    dijkstra = dijkstra_route(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
    )

    astar = astar_route(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
    )

    return {
        "dijkstra": _route_result_to_response(
            dijkstra,
            lg.source,
            lg.region,
        ),
        "astar": _route_result_to_response(
            astar,
            lg.source,
            lg.region,
        ),
        "source_snap_distance_m": round(src_dist, 1),
        "destination_snap_distance_m": round(dst_dist, 1),
        **traffic_meta,
    }


@router.post(
    "/route/optimize",
    response_model=OptimizeRouteResponse,
)
def route_optimize(req: RouteRequest):
    """
    Generate candidate routes and select among them using the
    QUBO + quantum-inspired simulated-annealing pipeline.

    In research mode the optimizer receives the same real historical
    METR-LA traffic snapshot used by the baseline endpoint.
    """
    lg = get_graph_state()
    G = lg.graph

    weights = _weights_from_request(req.weights)
    settings = get_settings()

    # ---------------------------------------------------------
    # SNAP SOURCE / DESTINATION TO THE REAL OSM GRAPH
    # ---------------------------------------------------------
    try:
        src_node, src_dist = nearest_node(
            G,
            req.source.lat,
            req.source.lon,
        )

        dst_node, dst_dist = nearest_node(
            G,
            req.destination.lat,
            req.destination.lon,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    # ---------------------------------------------------------
    # BUILD REAL OR DEMO TRAFFIC SNAPSHOT
    # ---------------------------------------------------------
    snapshot, traffic_meta = _build_traffic_snapshot(req)

    # ---------------------------------------------------------
    # RUN OPTIMIZATION
    # ---------------------------------------------------------
    result = run_optimization(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
        k_candidates=5,
        iterations=settings.OPTIMIZATION_ITERATIONS,
    )

    # ---------------------------------------------------------
    # NO CANDIDATE ROUTES
    # ---------------------------------------------------------
    if not result.found:
        return OptimizeRouteResponse(
            found=False,
            reason=result.reason,

            selected_route=None,
            candidate_routes=[],
            selected_index=None,

            # Optimizer correctness
            feasible_selection=False,
            was_repaired=False,
            exact_optimal_index=None,
            exact_optimal_cost=None,
            selected_cost=None,
            optimality_gap_pct=None,
            matches_exact_optimum=None,

            # QUBO / solver
            qubo_size=0,
            qubo_penalty=0.0,
            solver_iterations=0,
            solver_runtime_ms=0.0,
            solver_best_energy=0.0,
            solver_convergence_history=[],

            # Pipeline
            candidate_generation_time_ms=(
                result.candidate_generation_time_ms
            ),
            qubo_build_time_ms=0.0,
            total_pipeline_time_ms=(
                result.total_pipeline_time_ms
            ),

            # Network provenance
            graph_source=lg.source,
            region=lg.region,

            # Traffic provenance
            mode=traffic_meta["mode"],
            traffic_provenance=traffic_meta[
                "traffic_provenance"
            ],
            traffic_scenario=traffic_meta[
                "traffic_scenario"
            ],
            timestamp=traffic_meta.get("timestamp"),
        )

    # ---------------------------------------------------------
    # SUCCESSFUL OPTIMIZATION
    # ---------------------------------------------------------
    return OptimizeRouteResponse(
        found=True,
        reason=result.reason,

        selected_route=_route_result_to_response(
            result.selected_route,
            lg.source,
            lg.region,
        ),

        candidate_routes=[
            _route_result_to_response(
                r,
                lg.source,
                lg.region,
            )
            for r in result.candidate_routes
        ],

        selected_index=result.selected_index,

        # Optimizer correctness / transparency
        feasible_selection=result.feasible_selection,
        was_repaired=result.was_repaired,
        exact_optimal_index=result.exact_optimal_index,
        exact_optimal_cost=result.exact_optimal_cost,
        selected_cost=result.selected_cost,
        optimality_gap_pct=result.optimality_gap_pct,
        matches_exact_optimum=result.matches_exact_optimum,

        # QUBO / solver details
        qubo_size=result.qubo_size,
        qubo_penalty=result.qubo_penalty,
        solver_iterations=result.solver.iterations,
        solver_runtime_ms=result.solver.runtime_ms,
        solver_best_energy=result.solver.best_energy,
        solver_convergence_history=(
            result.solver.convergence_history
        ),

        # Pipeline timings
        candidate_generation_time_ms=(
            result.candidate_generation_time_ms
        ),
        qubo_build_time_ms=result.qubo_build_time_ms,
        total_pipeline_time_ms=result.total_pipeline_time_ms,

        # Network provenance
        graph_source=lg.source,
        region=lg.region,

        # Traffic provenance
        mode=traffic_meta["mode"],
        traffic_provenance=traffic_meta[
            "traffic_provenance"
        ],
        traffic_scenario=traffic_meta[
            "traffic_scenario"
        ],
        timestamp=traffic_meta.get("timestamp"),
    )
