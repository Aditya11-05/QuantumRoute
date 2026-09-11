"""
Synthetic training data generation for the congestion-prediction model.

HONESTY NOTE: There is no public, free, per-segment historical speed
dataset for a small Indian town readily available to a hackathon team
without a paid traffic-data subscription. Rather than pretend we have
one, we generate a synthetic dataset from an explicit, documented
generative process (see `_true_speed_ratio` below) that is DIFFERENT
FROM the deterministic formula the traffic simulator itself uses, and
includes genuine noise. This means the trained model is doing real
statistical learning (it has to recover a noisy nonlinear relationship
from features, not just invert a known formula), and its evaluation
metrics (MAE/RMSE/R^2 in train.py) are real, checkable numbers -
not fabricated. This is documented as a clear limitation: a fielded
system would replace this generator with real historical GPS/loop-
detector data.
"""
from __future__ import annotations

import random
from typing import List

import numpy as np
import pandas as pd

from app.ml.features import EdgeFeatureInput, build_feature_row, ROAD_TYPE_CODES, FEATURE_COLUMNS, TARGET_COLUMN

ROAD_TYPES = list(ROAD_TYPE_CODES.keys())


def _true_speed_ratio(
    hour: int,
    road_type: str,
    occupancy: float,
    incident: bool,
    lane_count: float,
    rng: random.Random,
) -> float:
    """
    The (synthetic) ground-truth generative process for speed_ratio.
    Deliberately nonlinear and noisy, and NOT identical to the
    formula used by app/simulation/traffic.py, so a model that just
    memorizes the simulator's formula would not automatically ace this
    dataset - it actually has to learn from correlated features like a
    real regression problem.
    """
    # Base congestion follows a smooth daily curve with two rush peaks.
    peak_am = np.exp(-((hour - 8.5) ** 2) / (2 * 1.6 ** 2))
    peak_pm = np.exp(-((hour - 18.5) ** 2) / (2 * 1.8 ** 2))
    daily_congestion = 0.15 + 0.55 * max(peak_am, peak_pm)

    # Occupancy has a nonlinear (super-linear) effect on slowdown.
    occupancy_effect = occupancy ** 1.6

    # More lanes absorb some congestion.
    lane_relief = min(0.15, 0.04 * (lane_count - 1))

    # Road type baseline free-flow reliability.
    type_bonus = {"primary": 0.05, "secondary": 0.02, "tertiary": 0.0, "residential": -0.02}
    base = type_bonus.get(road_type, 0.0)

    congestion = np.clip(daily_congestion + occupancy_effect - lane_relief - base, 0.02, 0.98)
    if incident:
        congestion = np.clip(congestion + rng.uniform(0.15, 0.35), 0.05, 0.99)

    speed_ratio = 1.0 - congestion
    # Measurement/process noise - real sensors are noisy.
    speed_ratio += rng.gauss(0, 0.04)
    return float(np.clip(speed_ratio, 0.03, 1.0))


def generate_training_dataset(n_samples: int = 6000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic (features, target) dataset for training the
    congestion/speed model. Returns a DataFrame with FEATURE_COLUMNS +
    TARGET_COLUMN.
    """
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    rows: List[dict] = []
    targets: List[float] = []

    for _ in range(n_samples):
        hour = rng.randint(0, 23)
        day_of_week = rng.randint(0, 6)
        road_type = rng.choice(ROAD_TYPES)
        road_length = float(np_rng.uniform(30, 450))
        lane_count = float(rng.choice([1, 1, 2, 2, 3]))
        speed_limit = {"residential": 30, "tertiary": 40, "secondary": 50, "primary": 60}[road_type]
        occupancy = float(np.clip(np_rng.beta(2, 3), 0, 1))
        incident = rng.random() < 0.05
        vehicle_count = int(occupancy * lane_count * 25)
        intersection_density = float(np_rng.uniform(0.5, 3.0))

        feat = EdgeFeatureInput(
            hour=hour, day_of_week=day_of_week, road_length_m=road_length,
            road_type=road_type, lane_count=lane_count, speed_limit_kmh=speed_limit,
            vehicle_count=vehicle_count, occupancy=occupancy, incident_flag=incident,
            intersection_density=intersection_density,
        )
        row = build_feature_row(feat)
        rows.append(row)

        target = _true_speed_ratio(hour, road_type, occupancy, incident, lane_count, rng)
        targets.append(target)

    df = pd.DataFrame(rows)[FEATURE_COLUMNS].copy()
    df[TARGET_COLUMN] = targets
    return df
