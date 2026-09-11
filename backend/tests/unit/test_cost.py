from __future__ import annotations

import pytest

from app.routing.cost import CostWeights, compute_edge_cost, INF_COST
from app.simulation.traffic import TrafficState


def _edge(highway="residential", length=100.0, maxspeed=30):
    return {"length": length, "highway": highway, "maxspeed": maxspeed, "lanes": 1}


def test_closed_edge_has_infinite_cost():
    edge = _edge()
    traffic = TrafficState(current_speed_kmh=0, vehicle_count=0, occupancy=1.0,
                            congestion_level=1.0, closed=True)
    result = compute_edge_cost(edge, traffic, CostWeights())
    assert result.total_cost == INF_COST
    assert result.closed is True


def test_higher_congestion_increases_cost():
    edge = _edge()
    weights = CostWeights()
    low = TrafficState(current_speed_kmh=28, vehicle_count=2, occupancy=0.1, congestion_level=0.1)
    high = TrafficState(current_speed_kmh=5, vehicle_count=20, occupancy=0.9, congestion_level=0.9)
    cost_low = compute_edge_cost(edge, low, weights).total_cost
    cost_high = compute_edge_cost(edge, high, weights).total_cost
    assert cost_high > cost_low


def test_incident_increases_cost():
    edge = _edge()
    weights = CostWeights()
    no_incident = TrafficState(current_speed_kmh=20, vehicle_count=5, occupancy=0.3,
                                congestion_level=0.3, incident_flag=False)
    incident = TrafficState(current_speed_kmh=20, vehicle_count=5, occupancy=0.3,
                             congestion_level=0.3, incident_flag=True)
    c1 = compute_edge_cost(edge, no_incident, weights).total_cost
    c2 = compute_edge_cost(edge, incident, weights).total_cost
    assert c2 > c1


def test_weight_shift_toward_congestion_biases_selection():
    """
    A longer but less congested edge should become cheaper than a
    shorter but heavily congested edge once congestion weight dominates.
    """
    short_congested = _edge(length=50)
    long_free = _edge(length=400)

    traffic_congested = TrafficState(current_speed_kmh=5, vehicle_count=20, occupancy=0.95, congestion_level=0.95)
    traffic_free = TrafficState(current_speed_kmh=30, vehicle_count=2, occupancy=0.05, congestion_level=0.05)

    distance_heavy_weights = CostWeights(travel_time=0.05, congestion=0.05, distance=0.85,
                                          fuel=0.02, intersection=0.02, incident=0.01).normalized()
    congestion_heavy_weights = CostWeights(travel_time=0.05, congestion=0.85, distance=0.05,
                                            fuel=0.02, intersection=0.02, incident=0.01).normalized()

    c_short_congested_distweight = compute_edge_cost(short_congested, traffic_congested, distance_heavy_weights).total_cost
    c_long_free_distweight = compute_edge_cost(long_free, traffic_free, distance_heavy_weights).total_cost
    assert c_short_congested_distweight < c_long_free_distweight, "distance-dominant weights should prefer the short edge"

    c_short_congested_congweight = compute_edge_cost(short_congested, traffic_congested, congestion_heavy_weights).total_cost
    c_long_free_congweight = compute_edge_cost(long_free, traffic_free, congestion_heavy_weights).total_cost
    assert c_long_free_congweight < c_short_congested_congweight, "congestion-dominant weights should prefer the free-flowing edge"


def test_weights_normalize_to_sum_one():
    w = CostWeights(travel_time=1, congestion=1, distance=1, fuel=1, intersection=1, incident=1).normalized()
    total = w.travel_time + w.congestion + w.distance + w.fuel + w.intersection + w.incident
    assert total == pytest.approx(1.0)


def test_zero_weights_raise():
    with pytest.raises(ValueError):
        CostWeights(0, 0, 0, 0, 0, 0).normalized()
