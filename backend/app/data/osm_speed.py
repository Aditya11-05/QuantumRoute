"""
Utilities for parsing OSM maxspeed attributes.

This module intentionally has no dependency on traffic simulation or
routing cost code, so it can be safely reused by both.
"""

from __future__ import annotations

import ast
import re
from typing import Optional


_MPH_TO_KMH = 1.609344
_KNOT_TO_KMH = 1.852
_MS_TO_KMH = 3.6


def parse_osm_maxspeed_kmh(value: object) -> Optional[float]:
    """
    Parse an OSM maxspeed attribute into km/h.

    Supported examples:
        35
        "35"
        "35 mph"
        "35 km/h"
        "35 knots"
        "10 m/s"
        "['35 mph', '30 mph']"
        ["35 mph", "30 mph"]

    For multiple values, the first valid numeric speed is used.

    Returns None when no valid speed can be extracted.
    """

    if value is None:
        return None

    # Handle lists/tuples/sets directly.
    if isinstance(value, (list, tuple, set)):
        for item in value:
            parsed = parse_osm_maxspeed_kmh(item)
            if parsed is not None:
                return parsed
        return None

    # Numeric OSM values are interpreted as km/h.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        speed = float(value)
        return speed if speed > 0 else None

    text = str(value).strip()

    if not text:
        return None

    # OSMnx/GraphML can produce stringified lists.
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed_list = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed_list = None

        if isinstance(parsed_list, (list, tuple, set)):
            return parse_osm_maxspeed_kmh(parsed_list)

    # Normalize whitespace and case.
    text = text.lower().strip()

    # Extract the first numeric value.
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text)
    if not match:
        return None

    speed = float(match.group(0))

    if speed <= 0:
        return None

    if "mph" in text:
        return speed * _MPH_TO_KMH

    if "knot" in text or "knots" in text:
        return speed * _KNOT_TO_KMH

    if "m/s" in text or "meter per second" in text:
        return speed * _MS_TO_KMH

    # Plain values and explicit km/h.
    return speed
