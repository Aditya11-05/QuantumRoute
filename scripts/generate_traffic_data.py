#!/usr/bin/env python3
"""
scripts/generate_traffic_data.py

Generates synthetic traffic snapshots for every scenario and saves them
as JSON under data/processed/ for offline inspection/demo use (the API
itself generates traffic on the fly, so this script is mainly for
research/inspection and for the benchmarking pipeline to have static
reference snapshots if desired).
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config.settings import get_settings  # noqa: E402
from app.routing.graph_loader import load_graph  # noqa: E402
from app.simulation.traffic import TrafficScenario, simulate_traffic  # noqa: E402


def main():
    settings = get_settings()
    result = load_graph(settings, force_synthetic=(settings.PROJECT_MODE == "demo"))
    G = result.graph

    out_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    for scenario in TrafficScenario:
        snap = simulate_traffic(G, scenario, seed=settings.DEMO_RANDOM_SEED)
        serializable = {
            "scenario": snap.scenario.value,
            "seed": snap.seed,
            "edges": {
                f"{u}_{v}_{k}": asdict(state) for (u, v, k), state in snap.states.items()
            },
        }
        out_path = out_dir / f"traffic_{scenario.value}.json"
        with open(out_path, "w") as f:
            json.dump(serializable, f, indent=2)
        vals = [s.congestion_level for s in snap.states.values()]
        print(f"{scenario.value:10s} -> {out_path.name}  (avg_congestion={sum(vals)/len(vals):.3f}, edges={len(vals)})")

    print(f"\nSaved {len(list(TrafficScenario))} traffic snapshots to {out_dir}")


if __name__ == "__main__":
    main()
