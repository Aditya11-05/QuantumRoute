from __future__ import annotations

from app.simulation.traffic import TrafficScenario, simulate_traffic


def test_simulation_is_deterministic_given_seed(synthetic_graph):
    s1 = simulate_traffic(synthetic_graph, TrafficScenario.HEAVY, seed=7)
    s2 = simulate_traffic(synthetic_graph, TrafficScenario.HEAVY, seed=7)
    for key in s1.states:
        assert s1.states[key].congestion_level == s2.states[key].congestion_level


def test_different_seeds_produce_different_traffic(synthetic_graph):
    s1 = simulate_traffic(synthetic_graph, TrafficScenario.HEAVY, seed=1)
    s2 = simulate_traffic(synthetic_graph, TrafficScenario.HEAVY, seed=2)
    diffs = sum(
        1 for k in s1.states
        if abs(s1.states[k].congestion_level - s2.states[k].congestion_level) > 1e-9
    )
    assert diffs > 0


def test_congestion_increases_with_scenario_severity(synthetic_graph):
    order = [TrafficScenario.LOW, TrafficScenario.MEDIUM, TrafficScenario.HEAVY, TrafficScenario.PEAK]
    avgs = []
    for scenario in order:
        snap = simulate_traffic(synthetic_graph, scenario, seed=42)
        vals = [s.congestion_level for s in snap.states.values()]
        avgs.append(sum(vals) / len(vals))
    assert avgs == sorted(avgs), f"Congestion should increase monotonically: {avgs}"


def test_closure_scenario_has_closed_edges(synthetic_graph):
    snap = simulate_traffic(synthetic_graph, TrafficScenario.CLOSURE, seed=42)
    closed = [s for s in snap.states.values() if s.closed]
    assert len(closed) > 0
    for s in closed:
        assert s.current_speed_kmh == 0.0


def test_incident_scenario_has_incident_edges(synthetic_graph):
    snap = simulate_traffic(synthetic_graph, TrafficScenario.INCIDENT, seed=42)
    incidents = [s for s in snap.states.values() if s.incident_flag]
    assert len(incidents) > 0


def test_missing_edge_returns_safe_default(synthetic_graph):
    snap = simulate_traffic(synthetic_graph, TrafficScenario.LOW, seed=42)
    state = snap.get(-999, -998, 0)  # nonexistent edge
    assert 0.0 <= state.congestion_level <= 1.0
    assert state.current_speed_kmh > 0
