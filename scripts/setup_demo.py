#!/usr/bin/env python3
"""
scripts/setup_demo.py

One-shot setup for a fresh clone: trains the ML model, generates
reference traffic snapshots, and runs a quick end-to-end sanity check
of the full pipeline (graph -> traffic -> cost -> baseline -> QUBO ->
optimizer) so you know the system actually works before your demo.

Usage:
    python scripts/setup_demo.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def run_step(name: str, fn):
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    fn()


def step_train_model():
    from app.ml.train import train_model
    report = train_model(n_samples=6000, seed=42,
                          model_path="../data/models/congestion_model.txt",
                          report_path="../data/models/training_report.json")
    print(f"Model trained: MAE={report.mae}, RMSE={report.rmse}, R2={report.r2}")


def step_generate_traffic():
    from app.config.settings import get_settings
    from app.routing.graph_loader import load_graph
    from app.simulation.traffic import TrafficScenario, simulate_traffic

    settings = get_settings()
    result = load_graph(settings, force_synthetic=True)
    for scenario in TrafficScenario:
        snap = simulate_traffic(result.graph, scenario, seed=settings.DEMO_RANDOM_SEED)
        vals = [s.congestion_level for s in snap.states.values()]
        print(f"  {scenario.value:10s} avg_congestion={sum(vals)/len(vals):.3f}")


def step_sanity_check_pipeline():
    from app.config.settings import get_settings
    from app.routing.graph_loader import load_graph
    from app.routing.baseline import dijkstra_route, astar_route
    from app.routing.cost import CostWeights
    from app.optimization.optimizer import run_optimization
    from app.simulation.traffic import TrafficScenario, simulate_traffic

    settings = get_settings()
    result = load_graph(settings, force_synthetic=True)
    G = result.graph
    nodes = list(G.nodes)
    src, dst = nodes[0], nodes[-1]

    snap = simulate_traffic(G, TrafficScenario.HEAVY, seed=settings.DEMO_RANDOM_SEED)
    weights = CostWeights(**settings.default_weights)

    d = dijkstra_route(G, src, dst, snap, weights)
    a = astar_route(G, src, dst, snap, weights)
    assert d.found and a.found, "Baseline routing failed sanity check"
    assert abs(d.total_cost - a.total_cost) < 1e-6, "Dijkstra/A* mismatch"
    print(f"  Dijkstra/A* OK: cost={d.total_cost:.4f}, dist={d.total_distance_m:.0f}m")

    opt = run_optimization(G, src, dst, snap, weights, iterations=1500)
    assert opt.found, "Optimization pipeline failed sanity check"
    print(f"  QUBO/Optimizer OK: qubo_size={opt.qubo_size}, selected_cost={opt.selected_route.total_cost:.4f}")

    print("\nAll sanity checks passed. The system is ready to run.")


def step_run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=str(BACKEND)
    )
    if result.returncode != 0:
        print("\nWARNING: some tests failed. Review output above before demoing.")
    else:
        print("\nAll backend tests passed.")


def main():
    run_step("Step 1/4: Training ML model", step_train_model)
    run_step("Step 2/4: Generating reference traffic snapshots", step_generate_traffic)
    run_step("Step 3/4: Running end-to-end pipeline sanity check", step_sanity_check_pipeline)
    run_step("Step 4/4: Running backend test suite", step_run_tests)
    print("\nSetup complete. Start the backend with:\n  cd backend && uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
