from __future__ import annotations

from app.routing.candidate_routes import generate_candidate_routes
from app.routing.cost import CostWeights
from app.simulation.traffic import TrafficScenario, simulate_traffic


def test_candidate_routes_are_distinct_and_ordered(synthetic_graph, graph_source_target):
    src, dst = graph_source_target
    snap = simulate_traffic(synthetic_graph, TrafficScenario.MEDIUM, seed=42)
    cs = generate_candidate_routes(synthetic_graph, src, dst, snap, CostWeights(), k=5)

    assert cs.returned_k > 0
    paths = [tuple(r.node_path) for r in cs.routes]
    assert len(set(paths)) == len(paths), "candidate routes must be distinct"

    costs = [r.total_cost for r in cs.routes]
    assert costs == sorted(costs), "candidate routes must be cost-ordered ascending"


def test_first_candidate_matches_dijkstra(synthetic_graph, graph_source_target):
    from app.routing.baseline import dijkstra_route

    src, dst = graph_source_target
    snap = simulate_traffic(synthetic_graph, TrafficScenario.HEAVY, seed=42)
    weights = CostWeights()
    d = dijkstra_route(synthetic_graph, src, dst, snap, weights)
    cs = generate_candidate_routes(synthetic_graph, src, dst, snap, weights, k=5)
    assert cs.routes[0].total_cost == d.total_cost


def test_k_is_respected(synthetic_graph, graph_source_target):
    src, dst = graph_source_target
    snap = simulate_traffic(synthetic_graph, TrafficScenario.LOW, seed=42)
    cs = generate_candidate_routes(synthetic_graph, src, dst, snap, CostWeights(), k=3)
    assert cs.returned_k <= 3
