from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.state import get_graph_state


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def src_dst():
    lg = get_graph_state()
    nodes = list(lg.graph.nodes(data=True))
    n1, n2 = nodes[0], nodes[-1]
    return (
        {"lat": n1[1]["y"], "lon": n1[1]["x"]},
        {"lat": n2[1]["y"], "lon": n2[1]["x"]},
    )


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system_status(client):
    r = client.get("/system/status")
    assert r.status_code == 200
    body = r.json()
    assert body["graph_source"] in {"synthetic", "osm", "osm_cache"}
    assert "quantum_disclaimer" in body


def test_docs_available(client):
    r = client.get("/docs")
    assert r.status_code == 200
    r = client.get("/openapi.json")
    assert r.status_code == 200


def test_map_regions(client):
    r = client.get("/map/regions")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_route_baseline(client, src_dst):
    src, dst = src_dst
    r = client.post("/route/baseline", json={"source": src, "destination": dst, "traffic_scenario": "medium"})
    assert r.status_code == 200
    body = r.json()
    assert body["dijkstra"]["found"]
    assert body["astar"]["found"]
    assert body["dijkstra"]["total_cost"] == pytest.approx(body["astar"]["total_cost"], abs=1e-6)


def test_route_baseline_invalid_scenario(client, src_dst):
    src, dst = src_dst
    r = client.post("/route/baseline", json={"source": src, "destination": dst, "traffic_scenario": "not_a_scenario"})
    assert r.status_code == 400


def test_route_optimize(client, src_dst):
    src, dst = src_dst
    r = client.post("/route/optimize", json={"source": src, "destination": dst, "traffic_scenario": "heavy"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["qubo_size"] >= 1
    assert body["selected_route"] is not None
    assert "quantum_disclaimer" in body
    assert "classical" in body["quantum_disclaimer"].lower()


def test_traffic_simulate(client):
    r = client.post("/traffic/simulate", json={"scenario": "peak", "seed": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["is_synthetic"] is True
    assert 0 <= body["avg_congestion"] <= 1


def test_traffic_simulate_invalid(client):
    r = client.post("/traffic/simulate", json={"scenario": "invalid_scenario"})
    assert r.status_code == 400


def test_traffic_predict(client):
    r = client.post("/traffic/predict", json={"hour": 8, "day_of_week": 1, "road_type": "primary", "occupancy": 0.7})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["predicted_speed_ratio"] <= 1


def test_traffic_current(client):
    r = client.get("/traffic/current", params={"scenario": "low"})
    assert r.status_code == 200


def test_optimization_status(client):
    r = client.get("/optimization/status")
    assert r.status_code == 200
    assert r.json()["solver"] == "simulated_annealing"


def test_model_info(client):
    r = client.get("/model/info")
    assert r.status_code == 200


def test_benchmark(client, src_dst):
    src, dst = src_dst
    r = client.post("/benchmark", json={
        "source": src, "destination": dst, "scenarios": ["low", "heavy"],
        "seed": 1, "iterations": 500,
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["scenarios"]) == 2
    for sc in body["scenarios"]:
        algos = {res["algorithm"] for res in sc["results"]}
        assert algos == {"dijkstra", "astar", "quantumroute"}


def test_malformed_route_request_returns_422(client):
    r = client.post("/route/baseline", json={"source": {"lat": "not_a_number", "lon": 78.9}, "destination": {"lat": 29.2, "lon": 78.9}})
    assert r.status_code == 422


def test_out_of_range_coordinates_rejected(client):
    r = client.post("/route/baseline", json={"source": {"lat": 999, "lon": 78.9}, "destination": {"lat": 29.2, "lon": 78.9}})
    assert r.status_code == 422
