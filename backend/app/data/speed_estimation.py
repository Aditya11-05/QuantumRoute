"""
Research-mode reference-speed estimation.

Separates:
1. Explicit OSM maxspeed values
2. METR-LA training-derived reference speeds
3. Empirical OSM highway-class fallback estimates

Fallback values are NOT observed traffic speeds or legal speed limits.
They are reference-speed estimates derived from explicit OSM maxspeed
values already present in the research graph.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from app.routing.cost import parse_osm_maxspeed_kmh


PROVENANCE_OSM = "REAL_GEOGRAPHIC"
PROVENANCE_SENSOR = "REAL_HISTORICAL"
PROVENANCE_ESTIMATED = "ESTIMATED_FROM_OSM_ATTRIBUTES"

MIN_CLASS_SPEED_SAMPLES = 30
DEFAULT_REFERENCE_SPEED_KMH = 56.33


@dataclass(frozen=True)
class ReferenceSpeed:
    speed_kmh: float
    provenance: str
    method: str


@dataclass(frozen=True)
class SensorReference:
    sensor_id: int
    speed_kmh: float
    provenance: str
    method: str


def _normalize_highway(value: object) -> str:
    """Normalize an OSM highway attribute."""

    if value is None:
        return "unknown"

    if isinstance(value, (list, tuple, set)):
        values = list(value)
        return (
            str(values[0]).strip().lower()
            if values
            else "unknown"
        )

    text = str(value).strip()

    if not text:
        return "unknown"

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, (list, tuple, set)):
                values = list(parsed)
                return (
                    str(values[0]).strip().lower()
                    if values
                    else "unknown"
                )

        except (ValueError, SyntaxError):
            pass

    return text.lower()


def _parse_lane_count(value: object) -> Optional[float]:
    """
    Parse an OSM lane count.

    Currently informational only. It is deliberately not used
    to modify reference speeds.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None

    if isinstance(value, (list, tuple, set)):
        for item in value:
            parsed = _parse_lane_count(item)

            if parsed is not None:
                return parsed

        return None

    text = str(value).strip()

    if not text:
        return None

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, (list, tuple, set)):
                for item in parsed:
                    parsed_value = _parse_lane_count(item)

                    if parsed_value is not None:
                        return parsed_value

                return None

        except (ValueError, SyntaxError):
            pass

    match = re.search(
        r"\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    number = float(match.group())

    return number if number > 0 else None


def load_sensor_reference_speeds(
    path: Path,
) -> Dict[int, SensorReference]:
    """Load training-only METR-LA sensor reference speeds."""

    if not path.exists():
        raise FileNotFoundError(
            f"Reference-speed file does not exist: {path}"
        )

    df = pd.read_csv(path)

    required = {
        "sensor_id",
        "reference_speed_kmh",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Reference-speed file is missing required columns: "
            f"{sorted(missing)}"
        )

    result: Dict[int, SensorReference] = {}

    for _, row in df.iterrows():
        sensor_id = int(row["sensor_id"])
        speed_kmh = float(row["reference_speed_kmh"])

        if speed_kmh <= 0:
            raise ValueError(
                f"Invalid reference speed for sensor "
                f"{sensor_id}: {speed_kmh}"
            )

        provenance = str(
            row.get(
                "provenance",
                PROVENANCE_SENSOR,
            )
        )

        method = str(
            row.get(
                "method",
                "sensor_p95_training_only",
            )
        )

        result[sensor_id] = SensorReference(
            sensor_id=sensor_id,
            speed_kmh=speed_kmh,
            provenance=provenance,
            method=method,
        )

    if not result:
        raise ValueError(
            "Reference-speed file contains no sensor records."
        )

    return result


def load_sensor_edge_reference_speeds(
    mapping_path: Path,
    reference_path: Path,
) -> Dict[Tuple[int, int, int], ReferenceSpeed]:
    """
    Combine sensor-to-edge mapping with training reference speeds.

    If multiple sensors map to the same directed edge, their
    training reference speeds are averaged.
    """

    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Sensor mapping file does not exist: {mapping_path}"
        )

    mapping = pd.read_csv(mapping_path)

    required = {
        "sensor_id",
        "matched_u",
        "matched_v",
        "matched_key",
        "status",
    }

    missing = required - set(mapping.columns)

    if missing:
        raise ValueError(
            "Sensor mapping file is missing required columns: "
            f"{sorted(missing)}"
        )

    references = load_sensor_reference_speeds(
        reference_path
    )

    grouped: Dict[
        Tuple[int, int, int],
        list[float],
    ] = {}

    for _, row in mapping.iterrows():

        if str(row["status"]).upper() != "MATCHED":
            continue

        sensor_id = int(row["sensor_id"])

        reference = references.get(sensor_id)

        if reference is None:
            raise ValueError(
                f"No training reference speed found "
                f"for mapped sensor {sensor_id}."
            )

        edge_key = (
            int(row["matched_u"]),
            int(row["matched_v"]),
            int(row["matched_key"]),
        )

        grouped.setdefault(edge_key, []).append(
            reference.speed_kmh
        )

    result: Dict[
        Tuple[int, int, int],
        ReferenceSpeed,
    ] = {}

    for edge_key, speeds in grouped.items():

        result[edge_key] = ReferenceSpeed(
            speed_kmh=float(
                sum(speeds) / len(speeds)
            ),
            provenance=PROVENANCE_SENSOR,
            method=(
                "mean_sensor_reference_speed_"
                "from_training_only"
            ),
        )

    return result


def build_empirical_osm_speed_priors(
    graph,
) -> Dict[str, float]:
    """
    Derive highway-class reference speeds from explicit OSM
    maxspeed values already present in this research graph.

    Median is used instead of mean.

    Classes with fewer than MIN_CLASS_SPEED_SAMPLES observations
    use the global empirical median instead.
    """

    by_highway = defaultdict(list)

    for _, _, _, edge_data in graph.edges(
        keys=True,
        data=True,
    ):
        speed = parse_osm_maxspeed_kmh(
            edge_data.get("maxspeed")
        )

        if speed is None:
            continue

        highway = _normalize_highway(
            edge_data.get("highway")
        )

        by_highway[highway].append(float(speed))

    all_speeds = [
        speed
        for speeds in by_highway.values()
        for speed in speeds
    ]

    if not all_speeds:
        raise ValueError(
            "Cannot build empirical OSM speed priors: "
            "the research graph contains no parseable "
            "maxspeed values."
        )

    all_speeds.sort()

    n = len(all_speeds)

    if n % 2:
        global_median = all_speeds[n // 2]
    else:
        global_median = (
            all_speeds[n // 2 - 1]
            + all_speeds[n // 2]
        ) / 2.0

    priors: Dict[str, float] = {}

    for highway, speeds in by_highway.items():

        if len(speeds) < MIN_CLASS_SPEED_SAMPLES:
            continue

        speeds = sorted(speeds)

        n_class = len(speeds)

        if n_class % 2:
            median = speeds[n_class // 2]
        else:
            median = (
                speeds[n_class // 2 - 1]
                + speeds[n_class // 2]
            ) / 2.0

        priors[highway] = float(median)

    priors["__global__"] = float(global_median)

    return priors


def estimate_edge_reference_speed(
    edge_data: Dict,
    edge_key: Tuple[int, int, int],
    sensor_edge_references: Dict[
        Tuple[int, int, int],
        ReferenceSpeed,
    ],
    osm_speed_priors: Dict[str, float],
) -> ReferenceSpeed:
    """
    Resolve reference speed using:

    1. Explicit OSM maxspeed
    2. Direct METR-LA sensor reference
    3. Empirical OSM highway-class median
    4. Empirical global OSM median
    """

    osm_speed = parse_osm_maxspeed_kmh(
        edge_data.get("maxspeed")
    )

    if osm_speed is not None:
        return ReferenceSpeed(
            speed_kmh=float(osm_speed),
            provenance=PROVENANCE_OSM,
            method="osm_explicit_maxspeed",
        )

    sensor_reference = sensor_edge_references.get(
        edge_key
    )

    if sensor_reference is not None:
        return sensor_reference

    highway = _normalize_highway(
        edge_data.get("highway")
    )

    class_speed = osm_speed_priors.get(
        highway
    )

    if class_speed is not None:
        return ReferenceSpeed(
            speed_kmh=float(class_speed),
            provenance=PROVENANCE_ESTIMATED,
            method=(
                "osm_empirical_highway_class_median:"
                f"{highway}"
            ),
        )

    global_speed = osm_speed_priors.get(
        "__global__"
    )

    if global_speed is None:
        raise ValueError(
            "Empirical OSM speed priors do not contain "
            "a global fallback."
        )

    return ReferenceSpeed(
        speed_kmh=float(global_speed),
        provenance=PROVENANCE_ESTIMATED,
        method="osm_empirical_global_median",
    )


def build_edge_reference_speeds(
    graph,
    sensor_mapping_path: Path,
    reference_speed_path: Path,
) -> Dict[
    Tuple[int, int, int],
    ReferenceSpeed,
]:
    """Build reference speeds for every directed edge."""

    sensor_references = (
        load_sensor_edge_reference_speeds(
            sensor_mapping_path,
            reference_speed_path,
        )
    )

    osm_speed_priors = (
        build_empirical_osm_speed_priors(
            graph
        )
    )

    result: Dict[
        Tuple[int, int, int],
        ReferenceSpeed,
    ] = {}

    for u, v, key, edge_data in graph.edges(
        keys=True,
        data=True,
    ):

        edge_key = (
            int(u),
            int(v),
            int(key),
        )

        result[edge_key] = (
            estimate_edge_reference_speed(
                edge_data=edge_data,
                edge_key=edge_key,
                sensor_edge_references=(
                    sensor_references
                ),
                osm_speed_priors=(
                    osm_speed_priors
                ),
            )
        )

    return result


def summarize_reference_speeds(
    reference_speeds: Dict[
        Tuple[int, int, int],
        ReferenceSpeed,
    ],
) -> Dict:
    """Summarize reference-speed provenance."""

    counts: Dict[str, int] = {}
    methods: Dict[str, int] = {}
    speeds = []

    for reference in reference_speeds.values():

        counts[reference.provenance] = (
            counts.get(
                reference.provenance,
                0,
            )
            + 1
        )

        methods[reference.method] = (
            methods.get(
                reference.method,
                0,
            )
            + 1
        )

        speeds.append(reference.speed_kmh)

    total = len(speeds)

    return {
        "total_edges": total,
        "provenance_counts": counts,
        "method_counts": methods,
        "min_speed_kmh": (
            min(speeds)
            if speeds
            else None
        ),
        "max_speed_kmh": (
            max(speeds)
            if speeds
            else None
        ),
        "mean_speed_kmh": (
            sum(speeds) / len(speeds)
            if speeds
            else None
        ),
    }
