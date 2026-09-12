"""
Real historical traffic adapter for METR-LA.

This module converts METR-LA sensor speed observations into the
TrafficSnapshot interface used by QuantumRoute's routing stack.

Data provenance:
    REAL_HISTORICAL

METR-LA provides sensor speed observations only. It does NOT provide:
    - vehicle counts
    - occupancy
    - incident labels
    - road closures

Those fields therefore remain unavailable rather than being fabricated.

Missing-value convention:
    METR-LA uses 0 as an encoded missing value. Zero observations are
    treated as missing and are never interpreted as 0 mph traffic.

Reference speeds:
    Congestion is calculated using sensor-specific reference speeds
    derived exclusively from the chronological training split.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Tuple

import networkx as nx
import pandas as pd

from app.simulation.traffic import TrafficSnapshot, TrafficState


@dataclass(frozen=True)
class SensorEdgeMapping:
    """Mapping from a METR-LA sensor to an OSM edge."""

    sensor_id: str
    u: int
    v: int
    key: int
    distance_m: float


class RealTrafficError(RuntimeError):
    """Raised when real traffic data cannot be used safely."""


def load_metr_la(
    path: str | Path,
    timestamp: str | pd.Timestamp,
) -> pd.Series:
    """
    Load one METR-LA observation at a requested timestamp.

    Returns:
        Series indexed by sensor ID with speed values in mph.

    Raises:
        RealTrafficError if the file/timestamp cannot be used.
    """
    path = Path(path)

    if not path.exists():
        raise RealTrafficError(f"METR-LA file not found: {path}")

    try:
        df = pd.read_hdf(path)
    except Exception as exc:
        raise RealTrafficError(
            f"Could not read METR-LA HDF5 file: {path}"
        ) from exc

    if not isinstance(df.index, pd.DatetimeIndex):
        raise RealTrafficError("METR-LA index must be a DatetimeIndex.")

    ts = pd.Timestamp(timestamp)

    if ts not in df.index:
        raise RealTrafficError(
            f"Timestamp {ts} is not present in METR-LA dataset."
        )

    row = df.loc[ts]

    # METR-LA encodes missing observations as zero.
    row = row.astype(float)
    row = row.where(row > 0)

    return row


def _mph_to_kmh(speed_mph: float) -> float:
    """Convert speed from miles/hour to kilometres/hour."""
    return speed_mph * 1.609344


def _derive_congestion(
    observed_speed_kmh: float,
    reference_speed_kmh: float,
) -> float:
    """
    Derive a bounded congestion score from observed speed.

    congestion = 0 -> observed speed equals/exceeds reference speed
    congestion = 1 -> observed speed approaches zero

    The reference speed must be supplied explicitly; it is not inferred
    from the current observation.
    """
    if reference_speed_kmh <= 0:
        raise ValueError("reference_speed_kmh must be positive.")

    ratio = observed_speed_kmh / reference_speed_kmh
    return max(0.0, min(1.0, 1.0 - ratio))


def build_real_traffic_snapshot(
    G: nx.MultiDiGraph,
    sensor_row: pd.Series,
    sensor_mappings: Mapping[str, SensorEdgeMapping],
    reference_speeds_kmh: Mapping[str, float],
) -> TrafficSnapshot:
    """
    Convert one METR-LA timestamp into an edge-level TrafficSnapshot.

    Only sensors with:
        - a valid (>0) METR-LA observation,
        - an explicit sensor-to-edge mapping, and
        - a valid sensor-specific reference speed

    contribute to the snapshot.

    For each sensor, congestion is calculated against that sensor's
    training-only reference speed before multiple sensors are aggregated
    onto the same OSM edge.

    Multiple sensors mapped to the same edge are aggregated using the
    arithmetic mean of their observed speeds and congestion values.

    Edges without an observation are omitted from the snapshot rather
    than assigned fabricated traffic values.
    """
    grouped: Dict[
        Tuple[int, int, int],
        list[Tuple[float, float]],
    ] = {}

    for sensor_id, raw_speed in sensor_row.items():
        sensor_id = str(sensor_id)

        if pd.isna(raw_speed):
            continue

        mapping = sensor_mappings.get(sensor_id)
        if mapping is None:
            continue

        reference_speed = reference_speeds_kmh.get(sensor_id)
        if reference_speed is None:
            raise RealTrafficError(
                f"No reference speed found for METR-LA sensor {sensor_id}."
            )

        reference_speed = float(reference_speed)

        if reference_speed <= 0:
            raise RealTrafficError(
                f"Invalid reference speed for sensor {sensor_id}: "
                f"{reference_speed}"
            )

        speed_mph = float(raw_speed)

        if speed_mph <= 0:
            continue

        observed_speed_kmh = _mph_to_kmh(speed_mph)

        congestion = _derive_congestion(
            observed_speed_kmh,
            reference_speed,
        )

        edge_key = (
            mapping.u,
            mapping.v,
            mapping.key,
        )

        grouped.setdefault(edge_key, []).append(
            (observed_speed_kmh, congestion)
        )

    states: Dict[Tuple[int, int, int], TrafficState] = {}

    for edge_key, observations in grouped.items():
        u, v, key = edge_key

        # If the mapping references an edge that no longer exists,
        # fail closed rather than silently attaching traffic elsewhere.
        if not G.has_edge(u, v, key):
            raise RealTrafficError(
                f"Sensor mapping references missing OSM edge: "
                f"{edge_key}"
            )

        observed_speed_kmh = sum(
            speed for speed, _ in observations
        ) / len(observations)

        congestion = sum(
            value for _, value in observations
        ) / len(observations)

        states[edge_key] = TrafficState(
            current_speed_kmh=round(observed_speed_kmh, 3),

            # METR-LA does not provide these variables.
            # They are retained only for compatibility with the existing
            # TrafficState interface and must not be interpreted as
            # measured values.
            vehicle_count=0,
            occupancy=0.0,
            incident_flag=False,
            closed=False,

            congestion_level=round(congestion, 6),
        )

    return TrafficSnapshot(
        scenario="real_historical",
        seed=0,
        states=states,
    )


def summarize_real_snapshot(
    snapshot: TrafficSnapshot,
) -> dict:
    """Return transparent metadata about the real-data snapshot."""

    speeds = [
        state.current_speed_kmh
        for state in snapshot.states.values()
        if state.current_speed_kmh > 0
    ]

    congestion = [
        state.congestion_level
        for state in snapshot.states.values()
    ]

    return {
        "provenance": "REAL_HISTORICAL",
        "observed_edge_count": len(snapshot.states),
        "speed_unit": "km/h",
        "mean_observed_speed_kmh": (
            round(sum(speeds) / len(speeds), 3)
            if speeds
            else None
        ),
        "mean_congestion": (
            round(sum(congestion) / len(congestion), 6)
            if congestion
            else None
        ),
        "vehicle_count_available": False,
        "occupancy_available": False,
        "incident_labels_available": False,
        "closure_labels_available": False,
        "reference_speed_provenance": "ESTIMATED_FROM_REAL_HISTORICAL_TRAINING",
        "reference_speed_method": "sensor_p95_training_only",
    }