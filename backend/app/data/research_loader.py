from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from app.data.real_traffic import SensorEdgeMapping, RealTrafficError
from app.data.speed_estimation import load_sensor_reference_speeds


def load_sensor_edge_mappings(
    path: Path,
) -> Dict[str, SensorEdgeMapping]:
    """
    Load validated METR-LA sensor -> OSM directed-edge mappings.

    Only MATCHED records are accepted.
    """

    if not path.exists():
        raise RealTrafficError(
            f"Sensor mapping file not found: {path}"
        )

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise RealTrafficError(
            f"Could not read sensor mapping file: {path}"
        ) from exc

    required = {
        "sensor_id",
        "matched_u",
        "matched_v",
        "matched_key",
        "distance_m",
        "status",
    }

    missing = required - set(df.columns)

    if missing:
        raise RealTrafficError(
            "Sensor mapping file is missing required columns: "
            f"{sorted(missing)}"
        )

    mappings: Dict[str, SensorEdgeMapping] = {}

    for _, row in df.iterrows():
        if str(row["status"]).upper() != "MATCHED":
            continue

        sensor_id = str(row["sensor_id"])

        if sensor_id in mappings:
            raise RealTrafficError(
                f"Duplicate MATCHED sensor mapping: {sensor_id}"
            )

        mappings[sensor_id] = SensorEdgeMapping(
            sensor_id=sensor_id,
            u=int(row["matched_u"]),
            v=int(row["matched_v"]),
            key=int(row["matched_key"]),
            distance_m=float(row["distance_m"]),
        )

    if not mappings:
        raise RealTrafficError(
            "Sensor mapping file contains no MATCHED sensors."
        )

    return mappings


def load_research_reference_speeds(
    path: Path,
) -> Dict[str, float]:
    """
    Load sensor-specific training-only METR-LA reference speeds.
    """

    references = load_sensor_reference_speeds(path)

    return {
        str(sensor_id): float(reference.speed_kmh)
        for sensor_id, reference in references.items()
    }


def validate_research_data(
    traffic_path: Path,
    mapping_path: Path,
    reference_path: Path,
) -> None:
    """Fail closed if required research artifacts are unavailable."""

    required = {
        "METR-LA traffic": traffic_path,
        "sensor-edge mapping": mapping_path,
        "reference speeds": reference_path,
    }

    missing = [
        f"{name}: {path}"
        for name, path in required.items()
        if not path.exists()
    ]

    if missing:
        raise RealTrafficError(
            "Required research artifacts are missing:\n"
            + "\n".join(missing)
        )
