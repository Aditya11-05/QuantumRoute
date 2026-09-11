from __future__ import annotations

import networkx as nx

from app.routing.graph_loader import load_graph
from app.config.settings import Settings


def test_synthetic_graph_is_deterministic():
    s = Settings(PROJECT_MODE="demo", DEMO_RANDOM_SEED=42)
    g1 = load_graph(s, force_synthetic=True).graph
    g2 = load_graph(s, force_synthetic=True).graph
    assert g1.number_of_nodes() == g2.number_of_nodes()
    assert g1.number_of_edges() == g2.number_of_edges()
    assert set(g1.nodes) == set(g2.nodes)


def test_synthetic_graph_is_connected(synthetic_graph):
    # every node should be able to reach every other node (weakly, since
    # some edges are one-way)
    assert nx.is_weakly_connected(synthetic_graph)


def test_synthetic_graph_has_required_edge_attributes(synthetic_graph):
    required = {"length", "highway", "maxspeed", "lanes", "name", "oneway"}
    for _, _, data in list(synthetic_graph.edges(data=True))[:20]:
        assert required.issubset(data.keys())
        assert data["length"] > 0


def test_synthetic_graph_has_node_coordinates(synthetic_graph):
    for _, data in list(synthetic_graph.nodes(data=True))[:20]:
        assert "x" in data and "y" in data
        assert -180 <= data["x"] <= 180
        assert -90 <= data["y"] <= 90


def test_demo_mode_never_touches_network(monkeypatch):
    """PROJECT_MODE=demo must never attempt an OSM download."""
    import app.routing.graph_loader as gl

    def fail(*args, **kwargs):
        raise AssertionError("Live OSM download should not be attempted in demo mode")

    monkeypatch.setattr(gl, "_try_download_osm", fail)
    s = Settings(PROJECT_MODE="demo")
    result = load_graph(s)
    assert result.source == "synthetic"
