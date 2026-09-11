#!/usr/bin/env python3
"""
scripts/train_model.py

Trains the LightGBM congestion/speed-ratio prediction model on
synthetic data and saves it + a training report to data/models/.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --n-samples 10000 --seed 7
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ml.train import train_model  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Train the QuantumRoute congestion prediction model")
    parser.add_argument("--n-samples", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Generating {args.n_samples} synthetic training samples (seed={args.seed})...")
    report = train_model(
        n_samples=args.n_samples,
        seed=args.seed,
        model_path="../data/models/congestion_model.txt",
        report_path="../data/models/training_report.json",
    )

    print("\n=== Training complete (real, measured metrics) ===")
    print(json.dumps(asdict(report), indent=2))
    print(
        "\nNote: this model is trained on SYNTHETIC data (see "
        "backend/app/ml/dataset.py). Metrics above are real evaluation "
        "results on a held-out synthetic test split, not fabricated, "
        "but they describe how well the model learned the synthetic "
        "generative process - not real-world traffic accuracy."
    )


if __name__ == "__main__":
    main()
