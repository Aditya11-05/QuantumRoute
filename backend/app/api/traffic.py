from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ml.features import EdgeFeatureInput
from app.schemas.traffic import (
    TrafficPredictRequest,
    TrafficPredictResponse,
    TrafficSimulateRequest,
    TrafficSummary,
)
from app.simulation.traffic import TrafficScenario, simulate_traffic
from app.state import get_graph_state, get_predictor

router = APIRouter(tags=["traffic"])


@router.post("/traffic/simulate", response_model=TrafficSummary)
def traffic_simulate(req: TrafficSimulateRequest):
    lg = get_graph_state()
    try:
        scenario = TrafficScenario(req.scenario.lower())
    except ValueError:
        valid = ", ".join(s.value for s in TrafficScenario)
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Valid options: {valid}")

    snap = simulate_traffic(lg.graph, scenario, seed=req.seed)
    states = list(snap.states.values())
    n = len(states) or 1
    return TrafficSummary(
        scenario=scenario.value,
        seed=req.seed,
        num_edges=len(states),
        avg_congestion=round(sum(s.congestion_level for s in states) / n, 4),
        avg_speed_kmh=round(sum(s.current_speed_kmh for s in states) / n, 2),
        num_incidents=sum(1 for s in states if s.incident_flag),
        num_closures=sum(1 for s in states if s.closed),
    )


@router.get("/traffic/current", response_model=TrafficSummary)
def traffic_current(scenario: str = "low", seed: int = 42):
    return traffic_simulate(TrafficSimulateRequest(scenario=scenario, seed=seed))


@router.post("/traffic/predict", response_model=TrafficPredictResponse)
def traffic_predict(req: TrafficPredictRequest):
    predictor = get_predictor()
    feature_input = EdgeFeatureInput(
        hour=req.hour, day_of_week=req.day_of_week, road_length_m=req.road_length_m,
        road_type=req.road_type, lane_count=req.lane_count, speed_limit_kmh=req.speed_limit_kmh,
        vehicle_count=req.vehicle_count, occupancy=req.occupancy, incident_flag=req.incident_flag,
        intersection_density=req.intersection_density,
    )
    result = predictor.predict(feature_input)
    return TrafficPredictResponse(
        predicted_speed_ratio=result.predicted_speed_ratio,
        predicted_congestion_level=result.predicted_congestion_level,
        inference_time_ms=result.inference_time_ms,
        model_loaded=result.model_loaded,
    )
