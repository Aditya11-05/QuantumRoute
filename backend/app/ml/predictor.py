"""
Inference wrapper around the trained LightGBM congestion model.

Used by the API (/traffic/predict) and can optionally be blended into
the cost function as an additional congestion signal alongside the
traffic simulator's own congestion_level (they are DIFFERENT signals:
the simulator produces the "ground truth" for a demo scenario, and the
ML model predicts what congestion *would be expected* given
time-of-day/road features - the gap between them is itself
informative and shown in the UI as "AI Prediction vs simulated actual").
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import lightgbm as lgb
import pandas as pd

from app.ml.features import EdgeFeatureInput, build_feature_row, FEATURE_COLUMNS


@dataclass
class PredictionResult:
    predicted_speed_ratio: float
    predicted_congestion_level: float
    inference_time_ms: float
    model_loaded: bool


class CongestionPredictor:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self._booster: Optional[lgb.Booster] = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self) -> None:
        if not self.model_path.exists():
            self._load_error = f"Model file not found at {self.model_path}. Run scripts/train_model.py first."
            return
        try:
            self._booster = lgb.Booster(model_file=str(self.model_path))
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"Failed to load model: {exc}"

    @property
    def is_ready(self) -> bool:
        return self._booster is not None

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def predict(self, feature_input: EdgeFeatureInput) -> PredictionResult:
        start = time.perf_counter()
        if self._booster is None:
            elapsed = (time.perf_counter() - start) * 1000
            # Explicit, honest fallback: if the model isn't trained/loaded
            # yet, we do NOT fabricate a prediction - we return a neutral
            # midpoint value and flag model_loaded=False so callers (and
            # the UI) can show that clearly rather than pretending.
            return PredictionResult(
                predicted_speed_ratio=0.6,
                predicted_congestion_level=0.4,
                inference_time_ms=round(elapsed, 3),
                model_loaded=False,
            )

        row = build_feature_row(feature_input)
        X = pd.DataFrame([row])[FEATURE_COLUMNS]
        pred = float(self._booster.predict(X)[0])
        pred = max(0.03, min(1.0, pred))
        elapsed = (time.perf_counter() - start) * 1000

        return PredictionResult(
            predicted_speed_ratio=round(pred, 4),
            predicted_congestion_level=round(1.0 - pred, 4),
            inference_time_ms=round(elapsed, 3),
            model_loaded=True,
        )
