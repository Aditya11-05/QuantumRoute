"""
Model training for congestion (speed_ratio) prediction.

MODEL CHOICE: LightGBM (gradient-boosted decision trees) regressor.
Justification:
  - Our features are a mix of categorical-ish integers (road_type_code,
    hour, day_of_week) and continuous values (occupancy, lengths) with
    clearly nonlinear, non-monotonic relationships to the target (e.g.
    two rush-hour peaks). Gradient-boosted trees handle this kind of
    tabular, mixed-type, nonlinear regression very well without manual
    feature crosses.
  - LightGBM specifically is fast to train (seconds on a laptop CPU,
    important since this needs to be reproducible on a student machine
    during a hackathon), handles the modest dataset size well (no need
    for GPU/deep learning), and gives us feature importances for free,
    which is useful when explaining the model to judges.
  - We are NOT using a deep learning model because our tabular feature
    set and dataset size (thousands, not millions, of rows) do not
    justify the complexity/compute cost of a neural network.

EVALUATION: we hold out a genuine test split (never seen during
training) and report MAE, RMSE, R^2 computed with scikit-learn's
metrics - these are the real, reproducible numbers, not fabricated.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.ml.dataset import generate_training_dataset
from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMN


@dataclass
class TrainingReport:
    model_type: str
    n_train: int
    n_test: int
    mae: float
    rmse: float
    r2: float
    training_time_sec: float
    feature_importances: dict
    params: dict


def train_model(
    n_samples: int = 6000,
    seed: int = 42,
    test_size: float = 0.2,
    model_path: str = "../data/models/congestion_model.txt",
    report_path: str = "../data/models/training_report.json",
) -> TrainingReport:
    df = generate_training_dataset(n_samples=n_samples, seed=seed)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    params = {
        "objective": "regression",
        "metric": "rmse",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 200,
        "min_child_samples": 15,
        "random_state": seed,
        "verbosity": -1,
    }

    start = time.perf_counter()
    model = lgb.LGBMRegressor(**params)
    model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    importances = dict(zip(FEATURE_COLUMNS, [int(v) for v in model.feature_importances_]))

    model_path_p = Path(model_path)
    if not model_path_p.is_absolute():
        model_path_p = (Path(__file__).resolve().parent.parent.parent / model_path).resolve()
    model_path_p.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(model_path_p))

    report = TrainingReport(
        model_type="LightGBM Regressor (LGBMRegressor)",
        n_train=len(X_train),
        n_test=len(X_test),
        mae=round(mae, 5),
        rmse=round(rmse, 5),
        r2=round(r2, 5),
        training_time_sec=round(elapsed, 3),
        feature_importances=importances,
        params=params,
    )

    report_path_p = Path(report_path)
    if not report_path_p.is_absolute():
        report_path_p = (Path(__file__).resolve().parent.parent.parent / report_path).resolve()
    report_path_p.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path_p, "w") as f:
        json.dump(asdict(report), f, indent=2)

    return report


if __name__ == "__main__":
    report = train_model()
    print(json.dumps(asdict(report), indent=2))
