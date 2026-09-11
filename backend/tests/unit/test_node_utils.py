from __future__ import annotations

import pytest

from app.routing.node_utils import haversine_m, nearest_node, bounding_box


def test_haversine_zero_distance():
    assert haversine_m(29.21, 78.95, 29.21, 78.95) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    # Roughly 1 degree of latitude ~= 111.32 km
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111_320, rel=0.01)


def test_nearest_node_returns_exact_match(synthetic_graph):
    any_node = next(iter(synthetic_graph.nodes))
    data = synthetic_graph.nodes[any_node]
    node_id, dist = nearest_node(synthetic_graph, data["y"], data["x"])
    assert node_id == any_node
    assert dist < 1.0  # meters


def test_nearest_node_empty_graph_raises():
    import networkx as nx
    empty = nx.MultiDiGraph()
    with pytest.raises(ValueError):
        nearest_node(empty, 0.0, 0.0)


def test_bounding_box_contains_all_nodes(synthetic_graph):
    bbox = bounding_box(synthetic_graph)
    for _, data in synthetic_graph.nodes(data=True):
        assert bbox["min_lat"] <= data["y"] <= bbox["max_lat"]
        assert bbox["min_lon"] <= data["x"] <= bbox["max_lon"]
