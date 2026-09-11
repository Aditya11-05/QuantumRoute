"""
Feature engineering for the congestion-prediction model.

We predict a CONTINUOUS target: `speed_ratio` = current_speed / free_flow_speed,
a value in (0, 1] where 1.0 means free-flow (no congestion) and values
near 0 mean near-gridlock. We predict speed_ratio rather than a
discrete "low/medium/high congestion" class because:
  (a) it's a strictly more informative signal for the cost function
      (compute_edge_cost can convert it straight into a speed / travel
      time, no bucket-boundary information loss), and
  (b) regression lets us report standard, checkable regression metrics
      (MAE, RMSE, R^2) computed against a genuine held-out test split -
      see train.py.

FEATURES (documented, all computable at inference time from the road
graph + current traffic snapshot, so there's no leakage of the target):
    hour                  - 0-23, hour of day
    day_of_week           - 0-6 (Mon=0)
    is_weekend            - 0/1
    road_length_m         - edge length in meters
    road_type_code        - integer code for highway class
    lane_count            - number of lanes
    speed_limit_kmh        - posted/free-flow speed
    historical_speed_ratio - a smoothed "typical" speed ratio for this
                              road_type/hour combination (synthetic
                              historical average, NOT the live value)
    vehicle_count          - simulated vehicles currently on the segment
    occupancy              - simulated occupancy (0-1)
    incident_flag          - 0/1
    intersection_density   - proxy: 1 / (avg segment length in the
                              local neighborhood), rough stand-in for
                              "how many intersections per km"
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "is_weekend",
    "road_length_m",
    "road_type_code",
    "lane_count",
    "speed_limit_kmh",
    "historical_speed_ratio",
    "vehicle_count",
    "occupancy",
    "incident_flag",
    "intersection_density",
]

TARGET_COLUMN = "speed_ratio"

ROAD_TYPE_CODES = {
    "residential": 0,
    "tertiary": 1,
    "secondary": 2,
    "primary": 3,
}

# Very rough, hand-specified "typical" congestion multiplier by hour of
# day, used ONLY to generate historical_speed_ratio features and
# synthetic training labels. This stands in for what would otherwise be
# a real historical-traffic aggregation; it is intentionally simple and
# documented as synthetic (see docs/ml_model.md and docs/limitations.md).
_HOURLY_CONGESTION_PROFILE = {
    0: 0.95, 1: 0.97, 2: 0.98, 3: 0.98, 4: 0.95, 5: 0.85,
    6: 0.70, 7: 0.45, 8: 0.35, 9: 0.55, 10: 0.65, 11: 0.65,
    12: 0.55, 13: 0.55, 14: 0.60, 15: 0.55, 16: 0.45, 17: 0.30,
    18: 0.25, 19: 0.35, 20: 0.55, 21: 0.70, 22: 0.85, 23: 0.90,
}


def historical_speed_ratio(hour: int, road_type: str) -> float:
    base = _HOURLY_CONGESTION_PROFILE.get(int(hour) % 24, 0.6)
    # Arterials (primary/secondary) hold speed a bit better under load
    # than small residential streets, which is a documented modeling
    # simplification, not a measured fact.
    bump = {"primary": 0.05, "secondary": 0.02, "tertiary": 0.0, "residential": -0.03}
    return float(np.clip(base + bump.get(road_type, 0.0), 0.05, 1.0))


@dataclass
class EdgeFeatureInput:
    hour: int
    day_of_week: int
    road_length_m: float
    road_type: str
    lane_count: float
    speed_limit_kmh: float
    vehicle_count: int
    occupancy: float
    incident_flag: bool
    intersection_density: float


def build_feature_row(f: EdgeFeatureInput) -> Dict:
    road_type_code = ROAD_TYPE_CODES.get(f.road_type, 0)
    return {
        "hour": int(f.hour),
        "day_of_week": int(f.day_of_week),
        "is_weekend": int(f.day_of_week >= 5),
        "road_length_m": float(f.road_length_m),
        "road_type_code": road_type_code,
        "lane_count": float(f.lane_count),
        "speed_limit_kmh": float(f.speed_limit_kmh),
        "historical_speed_ratio": historical_speed_ratio(f.hour, f.road_type),
        "vehicle_count": int(f.vehicle_count),
        "occupancy": float(f.occupancy),
        "incident_flag": int(f.incident_flag),
        "intersection_density": float(f.intersection_density),
    }


def features_to_dataframe(rows: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    return df[FEATURE_COLUMNS]
