# Machine Learning Model

## What it predicts

A LightGBM **regressor** predicts `speed_ratio` = current_speed /
free_flow_speed, a continuous value in (0, 1]. We predict this instead
of a discrete congestion class ("low/medium/high") because it converts
directly into a travel-time estimate without losing information at
bucket boundaries, and because it lets us report standard, checkable
regression metrics (MAE, RMSE, R²) rather than a confusion matrix that
would need arbitrary class boundaries we'd have to justify.

## Why LightGBM

- Our features are a mix of small-integer categoricals (`hour`,
  `day_of_week`, `road_type_code`) and continuous values (`occupancy`,
  `road_length_m`) with **nonlinear, non-monotonic** relationships to
  the target — e.g. two separate rush-hour peaks. Gradient-boosted
  decision trees handle this natively, without manual feature crosses
  or polynomial terms.
- It trains in well under a second on a laptop CPU for our dataset size
  (thousands of rows) — see `data/models/training_report.json` for the
  actual measured `training_time_sec`.
- It gives feature importances for free, useful for explaining the
  model to judges (see below).
- A deep neural network would be **overkill**: our dataset size and
  purely tabular feature set do not justify the added complexity,
  training instability, and compute cost of a neural approach. This is
  a direct instance of the "no overengineering" principle from the
  project brief.

## Training data — and why it's synthetic

There is no freely available, per-road-segment historical traffic-
speed dataset for a small town like Kashipur. Paying for a commercial
traffic-data API was out of scope for a hackathon prototype. Rather
than fabricate "real" data, `app/ml/dataset.py::generate_training_dataset`
generates data from an **explicit, documented generative process**:
a smooth two-peak daily congestion curve, a nonlinear occupancy effect,
lane-count relief, road-type effects, an incident bump, and Gaussian
measurement noise (`_true_speed_ratio`).

Critically, this generative process is **different from** the formula
`app/simulation/traffic.py` uses for the traffic simulator (different
functional form for the daily curve, different occupancy exponent,
different noise). This means the model has to genuinely learn a
relationship from correlated features — it cannot simply memorize or
invert the simulator's formula. This is what makes the evaluation
metrics below meaningful rather than circular.

## Features

See `app/ml/features.py::FEATURE_COLUMNS` for the authoritative list:
`hour`, `day_of_week`, `is_weekend`, `road_length_m`, `road_type_code`,
`lane_count`, `speed_limit_kmh`, `historical_speed_ratio`,
`vehicle_count`, `occupancy`, `incident_flag`, `intersection_density`.

All are computable at inference time from the graph and the current
traffic snapshot — none of them leak the target.

## Real, measured evaluation (from an actual training run)

```
model_type: LightGBM Regressor (LGBMRegressor)
n_train: 4800   n_test: 1200
MAE:  0.0348
RMSE: 0.0452
R²:   0.9683
training_time_sec: 0.155
```

These numbers come from `data/models/training_report.json`, produced
by actually running `python scripts/train_model.py` in this
environment — they are not invented. R² is high but **not 1.0**
(a suspiciously perfect score would indicate leakage or a fabricated
number) — the residual error corresponds to the injected Gaussian
noise in the generative process, which is exactly what we'd expect from
genuine, non-overfit learning on a controllable synthetic task.

Feature importances (LightGBM's split-count based importance) show
`hour` and `occupancy` as the two strongest predictors, followed by
`historical_speed_ratio` and `intersection_density` — consistent with
the generative process's actual functional form, which is itself a
form of validation ("the model learned what it should have learned").

## Honest limitation

**These metrics describe how well the model learned our synthetic
generative process — they say nothing about real-world traffic
prediction accuracy.** A fielded version of QuantumRoute would need to
replace `dataset.py`'s synthetic generator with real historical
GPS/loop-detector/toll-plaza data before these numbers could be
interpreted as "real-world accuracy." This is listed explicitly in
`docs/limitations.md`.
