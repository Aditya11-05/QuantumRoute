from __future__ import annotations

from app.ml.dataset import generate_training_dataset
from app.ml.features import EdgeFeatureInput, build_feature_row, FEATURE_COLUMNS, TARGET_COLUMN


def test_dataset_generation_shape():
    df = generate_training_dataset(n_samples=200, seed=1)
    assert len(df) == 200
    for col in FEATURE_COLUMNS + [TARGET_COLUMN]:
        assert col in df.columns


def test_dataset_target_in_valid_range():
    df = generate_training_dataset(n_samples=500, seed=1)
    assert (df[TARGET_COLUMN] >= 0).all()
    assert (df[TARGET_COLUMN] <= 1).all()


def test_dataset_is_deterministic_given_seed():
    df1 = generate_training_dataset(n_samples=100, seed=99)
    df2 = generate_training_dataset(n_samples=100, seed=99)
    assert df1.equals(df2)


def test_feature_row_has_all_columns():
    f = EdgeFeatureInput(
        hour=10, day_of_week=3, road_length_m=120, road_type="primary",
        lane_count=2, speed_limit_kmh=60, vehicle_count=15, occupancy=0.4,
        incident_flag=False, intersection_density=1.2,
    )
    row = build_feature_row(f)
    for col in FEATURE_COLUMNS:
        assert col in row


def test_is_weekend_flag():
    f_weekday = EdgeFeatureInput(hour=9, day_of_week=2, road_length_m=100, road_type="residential",
                                  lane_count=1, speed_limit_kmh=30, vehicle_count=5, occupancy=0.2,
                                  incident_flag=False, intersection_density=1.0)
    f_weekend = EdgeFeatureInput(hour=9, day_of_week=6, road_length_m=100, road_type="residential",
                                  lane_count=1, speed_limit_kmh=30, vehicle_count=5, occupancy=0.2,
                                  incident_flag=False, intersection_density=1.0)
    assert build_feature_row(f_weekday)["is_weekend"] == 0
    assert build_feature_row(f_weekend)["is_weekend"] == 1
