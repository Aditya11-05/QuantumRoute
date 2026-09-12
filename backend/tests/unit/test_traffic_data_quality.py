"""
test_traffic_data_quality.py

Offline unit tests for scripts/download_traffic_data.py's quality_report()
function. These tests use a SMALL, CONSTRUCTED, IN-MEMORY DataFrame — not
real METR-LA data — so they run without network access or the actual
metr-la.h5 file. The synthetic fixture is shaped to exercise:

  1. The 34272-timestamps x 207-sensors structure (scaled down here to a
     manageable size, since the point is to test the *code path*, not to
     reproduce the real file's row count).
  2. Zero-encoded-missing vs. NaN counted strictly separately.
  3. Timestamp-continuity / interval inference on both a clean and a
     gappy index.

This file must never be mistaken for a real-data validation — it tests
logic only. Real-data validation happens by running
`python scripts/download_traffic_data.py --check <real metr-la.h5 path>`
against the actual downloaded file, which is a separate, offline,
one-time manual step outside pytest.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from download_traffic_data import quality_report  # noqa: E402


def _write_h5(df: pd.DataFrame, tmp_path: Path) -> str:
    path = tmp_path / "synthetic_traffic.h5"
    df.to_hdf(path, key="df")
    return str(path)


def test_sensor_count_matches_expected_207(tmp_path):
    # 10 timestamps is plenty to exercise the code path; sensor count is
    # what's being checked against the hard-coded expectation of 207.
    idx = pd.date_range("2012-03-01", periods=10, freq="5min")
    df = pd.DataFrame(
        np.random.uniform(20, 65, size=(10, 207)), index=idx,
        columns=[f"sensor_{i}" for i in range(207)],
    )
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert report["n_sensors"] == 207
    assert report["sensor_count_matches_expected"] is True


def test_sensor_count_mismatch_is_reported_not_hidden(tmp_path):
    idx = pd.date_range("2012-03-01", periods=5, freq="5min")
    df = pd.DataFrame(
        np.random.uniform(20, 65, size=(5, 42)), index=idx,
        columns=[f"sensor_{i}" for i in range(42)],
    )
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert report["n_sensors"] == 42
    assert report["sensor_count_matches_expected"] is False


def test_zero_encoded_missing_and_nan_are_counted_separately(tmp_path):
    idx = pd.date_range("2012-03-01", periods=4, freq="5min")
    # 2 sensors, 4 timestamps = 8 cells. Deliberately mix zeros, NaNs, and
    # real-looking nonzero values so the counts can't be confused.
    data = np.array([
        [30.0, 0.0],
        [0.0, 45.5],
        [np.nan, 0.0],
        [50.0, np.nan],
    ])
    df = pd.DataFrame(data, index=idx, columns=["s1", "s2"])
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert report["total_observations"] == 8
    assert report["zero_encoded_missing_count"] == 3
    assert report["nan_count"] == 2
    # The two counts must remain distinct fields, not merged into one figure.
    assert report["zero_encoded_missing_count"] != report["nan_count"]
    assert report["nan_count"] + report["zero_encoded_missing_count"] < report["total_observations"]


def test_continuous_5min_index_has_no_gaps(tmp_path):
    idx = pd.date_range("2012-03-01", periods=100, freq="5min")
    df = pd.DataFrame(
        np.random.uniform(20, 65, size=(100, 3)), index=idx, columns=["s1", "s2", "s3"],
    )
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert report["inferred_sampling_interval_seconds"] == 300  # 5 minutes
    assert report["inferred_sampling_interval_minutes"] == 5.0
    assert report["n_timestamp_gaps"] == 0
    assert report["n_missing_timestamp_slots"] == 0
    assert report["timestamp_continuity_ok"] is True


def test_gappy_index_is_detected_not_silently_accepted(tmp_path):
    idx = pd.date_range("2012-03-01", periods=50, freq="5min").tolist()
    # Remove a chunk in the middle to create a real gap of 3 missing slots.
    del idx[20:23]
    df = pd.DataFrame(
        np.random.uniform(20, 65, size=(len(idx), 2)), index=idx, columns=["s1", "s2"],
    )
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert report["inferred_sampling_interval_seconds"] == 300
    assert report["n_timestamp_gaps"] == 1
    assert report["n_missing_timestamp_slots"] == 3
    assert report["timestamp_continuity_ok"] is False


def test_no_hardcoded_end_date_field_remains(tmp_path):
    """
    Regression test: an earlier version of this validator hard-coded an
    expected end date of 2012-06-30, which was wrong for the actual
    downloaded file (real end date: 2012-06-27 23:55:00). That field
    must not reappear.
    """
    idx = pd.date_range("2012-03-01", periods=10, freq="5min")
    df = pd.DataFrame(
        np.random.uniform(20, 65, size=(10, 207)), index=idx,
        columns=[f"sensor_{i}" for i in range(207)],
    )
    h5_path = _write_h5(df, tmp_path)

    report = quality_report(h5_path)
    assert "expected_time_range" not in report
    assert "time_range_matches_expected" not in report
    assert "first_timestamp" in report
    assert "last_timestamp" in report
