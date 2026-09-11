from __future__ import annotations

import pytest

from app.routing.baseline import dijkstra_route, astar_route
from app.routing.cost import CostWeights
from app.simulation.traffic import TrafficScenario, simulate_traffic


def test_dijkstra_finds_a_path(synthetic_graph, graph_source_target):
    src, dst = graph_source_target
    result = dijkstra_route(synthetic_graph, src, dst)
    assert result.found
    assert result.node_path[0] == src
    assert result.node_path[-1] == dst
    assert result.total_distance_m > 0
    assert result.num_edges == len(result.node_path) - 1


def test_astar_matches_dijkstra_optimal_cost(synthetic_graph, graph_source_target):
    """A* with our admissible heuristic must find the same optimal cost as Dijkstra."""
    src, dst = graph_source_target
    weights = CostWeights()
    for scenario in TrafficScenario:
        snap = simulate_traffic(synthetic_graph, scenario, seed=42)
        d = dijkstra_route(synthetic_graph, src, dst, snap, weights)
        a = astar_route(synthetic_graph, src, dst, snap, weights)
        if not d.found:
            assert not a.found
            continue
        assert a.found
        assert a.total_cost == pytest.approx(d.total_cost, abs=1e-6), (
            f"A* and Dijkstra disagree under scenario {scenario}: {a.total_cost} vs {d.total_cost}"
        )


def test_route_changes_when_traffic_changes(synthetic_graph):
    """Traffic must actually be able to change which route is cheapest."""
    nodes = list(synthetic_graph.nodes)
    src, dst = nodes[0], nodes[len(nodes) // 2]
    weights = CostWeights()

    low = simulate_traffic(synthetic_graph, TrafficScenario.LOW, seed=42)
    peak = simulate_traffic(synthetic_graph, TrafficScenario.PEAK, seed=42)

    r_low = dijkstra_route(synthetic_graph, src, dst, low, weights)
    r_peak = dijkstra_route(synthetic_graph, src, dst, peak, weights)

    assert r_low.found and r_peak.found
    # Cost must increase under worse traffic (travel time / congestion terms rise).
    assert r_peak.total_cost > r_low.total_cost


def test_no_path_when_disconnected():
    import networkx as nx
    G = nx.MultiDiGraph()
    G.add_node(1, x=0, y=0)
    G.add_node(2, x=1, y=1)
    # no edges at all -> disconnected
    result = dijkstra_route(G, 1, 2)
    assert not result.found
    assert result.reason is not None


def test_unknown_node_returns_not_found(synthetic_graph):
    result = dijkstra_route(synthetic_graph, -12345, -6789)
    assert not result.found
