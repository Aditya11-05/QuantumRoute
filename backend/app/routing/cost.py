"""
Multi-objective edge cost function.

Cost(edge) = w1*travel_time_norm + w2*congestion_norm + w3*distance_norm
           + w4*fuel_proxy_norm + w5*intersection_penalty_norm
           + w6*incident_penalty_norm

WHY NORMALIZE:
Each raw component lives on a different scale (seconds vs. meters vs. a
0..1 fraction). If we summed raw values, distance (hundreds of meters)
would completely dominate congestion (0..1), no matter what weight we
picked. Min-max normalizing each component against the *edges we are
actually evaluating in this request* (or a fixed reference scale, see
NORMALIZATION REFERENCE below) puts every term on a comparable [0,1]
scale before the weights are applied, so a weight of 0.30 genuinely
means "30% of the decision", not "30% of a number that happens to be
tiny".

WHY WEIGHTS MATTER / HOW TO CHOOSE THEM:
The weights encode a policy choice: "how much do we care about speed
vs. avoiding traffic vs. minimizing fuel vs. avoiding busy
intersections vs. avoiding incidents". There's no universally correct
setting - a delivery fleet minimizing fuel would set w4 high; an
ambulance dispatcher would set w1 (and incident-avoidance) high. We
expose these as request-level parameters (default from settings) so
the frontend's "Optimization Weights" sliders have a real, direct
effect on the resulting route rather than being cosmetic.

WHAT HAPPENS WHEN WEIGHTS CHANGE:
Because cost is a weighted sum over the same normalized components,
increasing w2 (congestion) relative to the others will systematically
bias route selection away from congested edges even if that means a
longer physical distance - this is asserted in
tests/unit/test_cost.py.

NORMALIZATION REFERENCE:
We use fixed, documented reference scales (rather than per-request
min/max) so that cost values are comparable across different requests
and so a single very extreme edge can't distort normalization for the
whole graph:
    travel_time : 0 - 180 seconds per edge
    distance    : 0 - 500 meters per edge
    fuel_proxy  : 0 - 1 (already a ratio, see below)
    congestion  : 0 - 1 (already a ratio, from the traffic simulator)
Values outside the reference range are clamped to [0, 1].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.simulation.traffic import TrafficState

INF_COST = float("inf")

# Reference scales used for min-max normalization (see module docstring).
_REF_TRAVEL_TIME_SEC = 180.0
_REF_DISTANCE_M = 500.0

_HIGHWAY_INTERSECTION_PENALTY = {
    # Rough proxy: more "important" road classes tend to have more
    # signalized/complex intersections at their endpoints. This is a
    # simplification, documented as such - see docs/algorithms.md.
    "primary": 0.8,
    "secondary": 0.5,
    "tertiary": 0.3,
    "residential": 0.15,
}

# Fuel proxy: rough relative fuel burn multiplier by driving condition.
# Idling / stop-start traffic burns proportionally more fuel per meter
# than free-flow driving. This is a simplified proxy, NOT a calibrated
# vehicle fuel model - documented in docs/limitations via docs/algorithms.md.
def _fuel_proxy(congestion: float, highway: str) -> float:
    base = 0.3 + 0.7 * congestion  # stop-start traffic burns more fuel/meter
    if highway == "primary":
        base *= 0.9  # steadier speeds on arterials, slightly more efficient
    return max(0.0, min(1.0, base))


@dataclass
class CostWeights:
    travel_time: float = 0.35
    congestion: float = 0.30
    distance: float = 0.15
    fuel: float = 0.10
    intersection: float = 0.05
    incident: float = 0.05

    def normalized(self) -> "CostWeights":
        total = (
            self.travel_time + self.congestion + self.distance
            + self.fuel + self.intersection + self.incident
        )
        if total <= 0:
            raise ValueError("Weights must sum to a positive value")
        return CostWeights(
            travel_time=self.travel_time / total,
            congestion=self.congestion / total,
            distance=self.distance / total,
            fuel=self.fuel / total,
            intersection=self.intersection / total,
            incident=self.incident / total,
        )


@dataclass
class EdgeCostBreakdown:
    total_cost: float
    travel_time_sec: float
    distance_m: float
    congestion: float
    fuel_proxy: float
    intersection_penalty: float
    incident_penalty: float
    closed: bool


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_edge_cost(
    edge_data: Dict,
    traffic: Optional[TrafficState],
    weights: CostWeights,
) -> EdgeCostBreakdown:
    """
    Compute the multi-objective cost for a single directed edge.

    `edge_data` is a NetworkX edge attribute dict (length, highway,
    maxspeed, lanes, ...). `traffic` is the simulated TrafficState for
    this edge (or None -> treated as free-flow / no data).
    """
    length_m = float(edge_data.get("length", 50.0) or 50.0)
    highway = str(edge_data.get("highway", "residential"))
    free_flow_speed_kmh = float(edge_data.get("maxspeed", 30) or 30)

    if traffic is not None and traffic.closed:
        return EdgeCostBreakdown(
            total_cost=INF_COST,
            travel_time_sec=INF_COST,
            distance_m=length_m,
            congestion=1.0,
            fuel_proxy=1.0,
            intersection_penalty=_HIGHWAY_INTERSECTION_PENALTY.get(highway, 0.2),
            incident_penalty=0.0,
            closed=True,
        )

    speed_kmh = traffic.current_speed_kmh if traffic else free_flow_speed_kmh
    speed_kmh = max(speed_kmh, 1.0)  # avoid division by zero
    travel_time_sec = (length_m / 1000.0) / speed_kmh * 3600.0

    congestion = traffic.congestion_level if traffic else 0.05
    incident_flag = traffic.incident_flag if traffic else False

    fuel = _fuel_proxy(congestion, highway)
    intersection_penalty = _HIGHWAY_INTERSECTION_PENALTY.get(highway, 0.2)
    incident_penalty = 1.0 if incident_flag else 0.0

    tt_norm = _clamp01(travel_time_sec / _REF_TRAVEL_TIME_SEC)
    dist_norm = _clamp01(length_m / _REF_DISTANCE_M)
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
