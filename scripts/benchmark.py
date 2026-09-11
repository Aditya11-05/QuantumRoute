#!/usr/bin/env python3
"""
scripts/benchmark.py

Runs Dijkstra vs A* vs QuantumRoute across all traffic scenarios for a
handful of source/destination pairs sampled from the loaded graph, and
saves the real results to data/benchmarks/benchmark_results.json.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --pairs 5 --iterations 3000
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.benchmarking.benchmark import run_benchmark  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.routing.graph_loader import load_graph  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run the QuantumRoute benchmark suite")
    parser.add_argument("--pairs", type=int, default=3, help="Number of random source/destination pairs to test")
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    settings = get_settings()
    result = load_graph(settings, force_synthetic=(settings.PROJECT_MODE == "demo"))
    G = result.graph
    nodes = list(G.nodes)

    rng = random.Random(args.seed)
    pairs = []
    for _ in range(args.pairs):
        src, dst = rng.sample(nodes, 2)
        pairs.append((src, dst))

    all_output = []
    for i, (src, dst) in enumerate(pairs):
        print(f"\n=== Pair {i+1}/{len(pairs)}: {src} -> {dst} ===")
        scenario_results = run_benchmark(G, src, dst, seed=args.seed, iterations=args.iterations)
        for sr in scenario_results:
            line = f"  {sr.scenario:10s} " + " | ".join(
                f"{r.algorithm}: cost={r.total_cost:.4f} t={r.runtime_ms:.2f}ms" for r in sr.results
            )
            print(line)
        all_output.append({
            "source_node": src,
            "destination_node": dst,
            "scenarios": [
                {"scenario": sr.scenario, "results": [asdict(r) for r in sr.results]}
                for sr in scenario_results
            ],
        })

    out_dir = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_results.json"
    with open(out_path, "w") as f:
        json.dump({
            "graph_source": result.source,
            "region": result.region,
            "iterations": args.iterations,
            "seed": args.seed,
            "pairs": all_output,
        }, f, indent=2)

    print(f"\nSaved benchmark results to {out_path}")
    print(
        "\nReminder: QuantumRoute's candidate-route QUBO can at best TIE "
        "Dijkstra/A* on cost (Dijkstra's own optimal path is always among "
        "the candidates), and can score slightly worse if the annealer "
        "hasn't converged. See docs/benchmarking.md for the honest "
        "interpretation of these numbers."
    )


if __name__ == "__main__":
    main()
