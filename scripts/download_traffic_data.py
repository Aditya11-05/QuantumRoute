"""
download_traffic_data.py

METR-LA traffic readings (metr-la.h5) are distributed via Google Drive /
Baidu Yun, linked from https://github.com/liyaguang/DCRNN. This host is
not reachable from a locked-down sandbox, and cannot be scripted with a
plain `requests.get` because Google Drive requires a browser-confirmed
download for files this size. YOU must fetch the file once, manually or
via gdown, on a machine with normal internet access:

    pip install gdown
    # Get the current Drive file ID from the DCRNN README (it can change):
    # https://github.com/liyaguang/DCRNN -> "Data Preparation" section
    gdown --id <FILE_ID_FROM_DCRNN_README> -O data/raw/metr_la/metr-la.h5

    # Also grab the graph structure files referenced in that same README:
    #   data/sensor_graph/graph_sensor_locations.csv  (already verified — see
    #       data/raw/metr_la/sensor_locations_VERIFIED_SAMPLE.csv for the
    #       207-row sample pulled in this session; re-download the
    #       authoritative copy from GitHub directly to be safe:)
    curl -L -o data/raw/metr_la/graph_sensor_locations.csv \\
        https://raw.githubusercontent.com/liyaguang/DCRNN/master/data/sensor_graph/graph_sensor_locations.csv
    curl -L -o data/raw/metr_la/adj_mx.pkl \\
        https://raw.githubusercontent.com/liyaguang/DCRNN/master/data/sensor_graph/adj_mx.pkl
    curl -L -o data/raw/metr_la/distances_la_2012.csv \\
        https://raw.githubusercontent.com/liyaguang/DCRNN/master/data/sensor_graph/distances_la_2012.csv

Once metr-la.h5 is in data/raw/metr_la/, run THIS script to validate it
and produce the Step-4 data quality report. This script does NOT
generate any data — it only reads and reports on what you downloaded.

Note: the actual file's timestamp range was verified (2026-09-13) to run
2012-03-01 00:00:00 to 2012-06-27 23:55:00 (34,272 timestamps x 207
sensors, 5-minute interval) — NOT through 2012-06-30 as some secondary
sources state. This script infers the sampling interval and timestamp
continuity from the file itself rather than checking against a
hard-coded end date.

Usage:
    pip install pandas tables
    python scripts/download_traffic_data.py --check data/raw/metr_la/metr-la.h5
"""
import argparse
import json
import sys
from pathlib import Path


def quality_report(h5_path: str):
    import pandas as pd
    import numpy as np

    df = pd.read_hdf(h5_path)
    # DCRNN stores this as a DataFrame: index = timestamp, columns = sensor_id, values = speed (mph)

    n_timestamps, n_sensors = df.shape
    values = df.values.astype(float)

    # METR-LA encodes missing readings as 0.0 (a physically impossible speed
    # for a loop detector), per the DCRNN paper and follow-up work (e.g.
    # Graph WaveNet, STGCN). A zero here means "no observation", NOT "the
    # road was empty" or "speed was measured as 0 mph". We count zeros and
    # NaNs SEPARATELY and never merge or convert one into the other in this
    # phase — that's a preprocessing-phase decision, not a validation one.
    n_total = values.size
    n_zero = int((values == 0.0).sum())
    n_nan = int(np.isnan(values).sum())

    nonzero = values[values > 0.0]

    # --- Timestamp continuity / sampling interval, inferred from the data
    # itself rather than assumed. Any previous hard-coded expected end date
    # was wrong for this real file (it actually ends 2012-06-27, not
    # 2012-06-30) and has been removed rather than patched with a new guess.
    index = df.index
    if not isinstance(index, pd.DatetimeIndex):
        index = pd.to_datetime(index)
    diffs = index.to_series().diff().dropna()

    if len(diffs) > 0:
        # Mode of the gaps = the actual sampling interval, not an assumption.
        inferred_interval = diffs.mode().iloc[0]
        inferred_interval_seconds = int(inferred_interval.total_seconds())

        expected_n_timestamps = int(
            (index.max() - index.min()) / inferred_interval
        ) + 1
        n_gaps = int((diffs != inferred_interval).sum())
        # Total "missing slots" implied by gaps larger than one interval.
        missing_slots = 0
        for d in diffs[diffs != inferred_interval]:
            steps = d / inferred_interval
            # steps should be an integer number of intervals if the clock
            # just skipped some slots; if it isn't, that's itself worth flagging.
            missing_slots += max(int(round(steps)) - 1, 0)
    else:
        inferred_interval_seconds = None
        expected_n_timestamps = n_timestamps
        n_gaps = 0
        missing_slots = 0

    report = {
        "file": str(h5_path),
        "n_timestamps": int(n_timestamps),
        "n_sensors": int(n_sensors),
        "expected_n_sensors": 207,
        "sensor_count_matches_expected": n_sensors == 207,
        "total_observations": int(n_total),
        "zero_encoded_missing_count": n_zero,
        "zero_encoded_missing_pct": round(100.0 * n_zero / n_total, 3),
        "nan_count": n_nan,
        "note": (
            "zero_encoded_missing_count and nan_count are reported separately "
            "and are NOT combined: zeros represent METR-LA's missing-value "
            "encoding, not literal 0 mph readings, and are not treated as NaN "
            "or imputed at this stage."
        ),
        "min_speed_mph_nonzero": float(nonzero.min()) if nonzero.size else None,
        "max_speed_mph_nonzero": float(nonzero.max()) if nonzero.size else None,
        "mean_speed_mph_nonzero": float(nonzero.mean()) if nonzero.size else None,
        "first_timestamp": str(index.min()),
        "last_timestamp": str(index.max()),
        "inferred_sampling_interval_seconds": inferred_interval_seconds,
        "inferred_sampling_interval_minutes": (
            round(inferred_interval_seconds / 60.0, 3) if inferred_interval_seconds is not None else None
        ),
        "expected_n_timestamps_at_inferred_interval": expected_n_timestamps,
        "n_timestamp_gaps": n_gaps,
        "n_missing_timestamp_slots": missing_slots,
        "timestamp_continuity_ok": n_timestamps == expected_n_timestamps,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", type=str, required=True, help="Path to metr-la.h5 to validate")
    parser.add_argument("--out", type=str, default="data/processed/metr_la_quality_report.json")
    args = parser.parse_args()

    if not Path(args.check).exists():
        print(f"ERROR: {args.check} not found. Follow the module docstring instructions "
              f"to download it first — this script will not fabricate a report.", file=sys.stderr)
        sys.exit(1)

    try:
        import pandas  # noqa
        import tables  # noqa: F401  (pytables backend for HDF5)
    except ImportError:
        print("ERROR: run `pip install pandas tables` first.", file=sys.stderr)
        sys.exit(1)

    report = quality_report(args.check)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nSaved to {args.out}")
    if not report["sensor_count_matches_expected"]:
        print("WARNING: sensor count does not match the expected 207 — verify you downloaded the correct file.")
    if not report["timestamp_continuity_ok"]:
        print(
            f"WARNING: timestamp index is not fully continuous at the inferred "
            f"{report['inferred_sampling_interval_seconds']}s interval — "
            f"{report['n_timestamp_gaps']} gap(s) covering "
            f"{report['n_missing_timestamp_slots']} missing slot(s) between "
            f"{report['first_timestamp']} and {report['last_timestamp']}. "
            f"This is a real property of the file, not an error to silently fix here."
        )


if __name__ == "__main__":
    main()
