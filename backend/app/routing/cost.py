"""
Multi-objective edge cost function.

The cost combines:
    - travel time
    - congestion
    - distance
    - fuel proxy
    - intersection penalty
    - incident penalty

Research-mode note:
    OSM maxspeed values are parsed explicitly. Missing or unusable
    maxspeed values are NOT silently replaced with an arbitrary
    hard-coded speed.

    Missing-speed estimation is handled separately from this parser.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.simulation.traffic import TrafficState
from app.data.osm_speed import parse_osm_maxspeed_kmh

@dataclass(frozen=True)
class CostWeights:
    """Weights for the multi-objective routing cost."""

    travel_time: float = 0.40
    congestion: float = 0.25
    distance: float = 0.15
    fuel: float = 0.10
    intersection: float = 0.05
    incident: float = 0.05

    def normalized(self) -> "CostWeights":
        """Return weights normalized so that they sum to 1."""
        total = (
            self.travel_time
            + self.congestion
            + self.distance
            + self.fuel
            + self.intersection
            + self.incident
        )

        if total <= 0:
            raise ValueError("At least one cost weight must be positive.")

        return CostWeights(
            travel_time=self.travel_time / total,
            congestion=self.congestion / total,
            distance=self.distance / total,
            fuel=self.fuel / total,
            intersection=self.intersection / total,
            incident=self.incident / total,
        )


@dataclass(frozen=True)
class EdgeCostBreakdown:
    """Detailed cost components for one directed edge."""

    total_cost: float
    travel_time_sec: float
    distance_m: float
    congestion: float
    fuel_proxy: float
    intersection_penalty: float
    incident_penalty: float
    closed: bool = False


INF_COST = float("inf")

_REF_TRAVEL_TIME_SEC = 180.0
_REF_DISTANCE_M = 500.0

_HIGHWAY_INTERSECTION_PENALTY = {
    "primary": 0.8,
    "secondary": 0.5,
    "tertiary": 0.3,
    "residential": 0.15,
}


def _fuel_proxy(congestion: float, highway: str) -> float:
    """
    Simplified relative fuel-burn proxy.

    This is NOT a calibrated vehicle fuel-consumption model.
    """
    base = 0.3 + 0.7 * congestion

    if highway == "primary":
        base *= 0.9

    return max(0.0, min(1.0, base))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_edge_cost(
    edge_data: Dict,
    traffic: Optional[TrafficState],
    weights: CostWeights,
) -> EdgeCostBreakdown:
    """
    Compute the multi-objective cost for one directed edge.

    `edge_data` is a NetworkX edge attribute dictionary.

    `traffic` may contain an observed/estimated current speed.

    If traffic is unavailable and OSM has no explicit maxspeed, this
    function currently raises ValueError rather than inventing a speed.

    A separate research speed-estimation layer will provide a defensible
    fallback for those edges.
    """
    length_m = float(edge_data.get("length", 50.0) or 50.0)

    highway_value = edge_data.get("highway", "residential")

    if isinstance(highway_value, (list, tuple, set)):
        highway = str(next(iter(highway_value), "residential"))
    else:
        highway = str(highway_value)

    osm_speed_kmh = parse_osm_maxspeed_kmh(
        edge_data.get("maxspeed")
    )

    if traffic is not None and traffic.closed:
        return EdgeCostBreakdown(
            total_cost=INF_COST,
            travel_time_sec=INF_COST,
            distance_m=length_m,
            congestion=1.0,
            fuel_proxy=1.0,
            intersection_penalty=_HIGHWAY_INTERSECTION_PENALTY.get(
                highway,
                0.2,
            ),
            incident_penalty=0.0,
            closed=True,
        )

    if traffic is not None:
        speed_kmh = float(traffic.current_speed_kmh)
    elif osm_speed_kmh is not None:
        speed_kmh = osm_speed_kmh
    else:
        raise ValueError(
            "No usable speed is available for this edge. "
            "OSM maxspeed is missing or invalid, and no traffic "
            "observation was supplied. Research mode must provide "
            "a documented speed estimate instead of using an "
            "arbitrary default."
        )

    speed_kmh = max(speed_kmh, 1.0)

    travel_time_sec = (
        (length_m / 1000.0)
        / speed_kmh
        * 3600.0
    )

    congestion = (
        float(traffic.congestion_level)
        if traffic is not None
        else 0.0
    )

    incident_flag = (
        bool(traffic.incident_flag)
        if traffic is not None
        else False
    )

    fuel = _fuel_proxy(congestion, highway)

    intersection_penalty = _HIGHWAY_INTERSECTION_PENALTY.get(
        highway,
        0.2,
    )

    incident_penalty = 1.0 if incident_flag else 0.0

    tt_norm = _clamp01(
        travel_time_sec / _REF_TRAVEL_TIME_SEC
    )

    dist_norm = _clamp01(
        length_m / _REF_DISTANCE_M
    )

    congestion_norm = _clamp01(congestion)
    fuel_norm = _clamp01(fuel)
    intersection_norm = _clamp01(intersection_penalty)
    incident_norm = _clamp01(incident_penalty)

    total = (
        weights.travel_time * tt_norm
        + weights.congestion * congestion_norm
        + weights.distance * dist_norm
        + weights.fuel * fuel_norm
        + weights.intersection * intersection_norm
        + weights.incident * incident_norm
    )

    return EdgeCostBreakdown(
        total_cost=total,
        travel_time_sec=travel_time_sec,
        distance_m=length_m,
        congestion=congestion,
        fuel_proxy=fuel,
        intersection_penalty=intersection_penalty,
        incident_penalty=incident_penalty,
        closed=False,
    )