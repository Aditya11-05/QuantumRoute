"""
download_osm_network.py

Downloads a REAL OpenStreetMap road network via OSMnx/Overpass.

Two supported modes:

1. --bbox-from-sensors data/raw/metr_la/sensor_locations.csv --buffer-km 2
   Downloads the network clipped to the bounding box of the given sensor
   coordinate file, expanded by a buffer (so sensors near the edge still
   map onto a real segment). This is the mode used for the primary
   research pipeline (METR-LA network + METR-LA traffic, geographically matched).

2. --place "Kashipur, Uttarakhand, India"
   Downloads the named place's road network directly via Nominatim geocoding.
   This is the "supported Indian location" demo network. NOTE: no real
   traffic dataset is geographically matched to this network — see
   data/sources.yaml (kashipur_synthetic_traffic) for how traffic is
   handled for this location.

Requires internet access to:
  - https://nominatim.openstreetmap.org (geocoding, --place mode only)
  - https://overpass-api.de (road network extraction)
These are NOT reachable from a locked-down sandbox. Run this on a normal
machine (your laptop, a Colab notebook, a CI runner with open egress).

Targets OSMnx >= 2.0 (developed/tested against 2.0.1, Python 3.11.15).
It will refuse to run against an installed OSMnx 1.x, since this script
uses the 2.x `graph_from_bbox(bbox=...)` tuple signature (the 1.x
north=/south=/east=/west= kwargs were removed, not just deprecated, in
2.0.0 — see https://github.com/gboeing/osmnx/issues/1123).

Usage:
    pip install -r backend/requirements.txt   # pins osmnx==2.0.1

    # Primary research pipeline (matches the verified METR-LA sensors)
    python scripts/download_osm_network.py \
        --bbox-from-sensors data/raw/metr_la/sensor_locations.csv \
        --buffer-km 2 \
        --out data/raw/osm/metr_la_network.graphml

    # Indian demo location
    python scripts/download_osm_network.py \
        --place "Kashipur, Uttarakhand, India" \
        --out data/raw/osm/kashipur_network.graphml

Output:
    A .graphml file (real OSM graph: nodes, edges, geometry, highway type,
    lanes, maxspeed, oneway, name — whatever OSM has tagged) plus a
    .json metadata sidecar recording download date, place/bbox, node/edge
    counts, and the OSMnx/osm data version, for reproducibility (req. #32).

This script performs NO synthetic data generation. If the download fails
(e.g. no network egress, Overpass rate limit, invalid place name), it
exits with a clear error — it does NOT fall back to a fake graph.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def bbox_from_sensor_csv(path: str, buffer_km: float):
    lats, lons = [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lats.append(float(row["latitude"]))
            lons.append(float(row["longitude"]))
    if not lats:
        raise ValueError(f"No sensor rows found in {path}")

    # 1 degree latitude ~= 111 km everywhere.
    # 1 degree longitude ~= 111 km * cos(latitude); use mean lat for the correction.
    import math

    mean_lat = sum(lats) / len(lats)
    dlat = buffer_km / 111.0
    dlon = buffer_km / (111.0 * max(math.cos(math.radians(mean_lat)), 1e-6))

    north = max(lats) + dlat
    south = min(lats) - dlat
    east = max(lons) + dlon
    west = min(lons) - dlon
    return north, south, east, west


def download_by_bbox(north, south, east, west, out_path: Path, network_type: str):
    import osmnx as ox

    # OSMnx 2.0 breaking change (see the v2 migration guide,
    # github.com/gboeing/osmnx/issues/1123): graph_from_bbox no longer
    # accepts separate north=/south=/east=/west= keyword args — those
    # were REMOVED (not just deprecated) in 2.0.0. It now takes a single
    # positional `bbox` tuple ordered (west, south, east, north), i.e.
    # (left, bottom, right, top). Passing the old 1.x keyword args
    # against osmnx>=2 raises a TypeError, so we assemble the tuple
    # explicitly rather than relying on kwarg compatibility.
    bbox = (west, south, east, north)  # (left, bottom, right, top) per OSMnx 2.x

    ox.settings.log_console = True
    print(f"[download_osm_network] Querying Overpass for bbox "
          f"(west={west:.5f}, south={south:.5f}, east={east:.5f}, north={north:.5f}) "
          f"network_type={network_type}")
    G = ox.graph_from_bbox(bbox, network_type=network_type)
    return G, {"mode": "bbox", "north": north, "south": south, "east": east, "west": west}


def download_by_place(place: str, out_path: Path, network_type: str):
    import osmnx as ox

    ox.settings.log_console = True
    print(f"[download_osm_network] Geocoding + querying Overpass for place='{place}'")
    G = ox.graph_from_place(place, network_type=network_type)
    return G, {"mode": "place", "place": place}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--place", type=str, default=None,
                         help="Named place to geocode via Nominatim, e.g. 'Kashipur, Uttarakhand, India'")
    parser.add_argument("--bbox-from-sensors", type=str, default=None,
                         help="Path to a sensor CSV with latitude/longitude columns; bbox is derived from it")
    parser.add_argument("--buffer-km", type=float, default=2.0,
                         help="Buffer in km added around the sensor bbox (default: 2.0)")
    parser.add_argument("--network-type", type=str, default="drive",
                         choices=["drive", "drive_service", "all", "bike", "walk"],
                         help="OSMnx network type filter (default: drive)")
    parser.add_argument("--out", type=str, required=True, help="Output .graphml path")
    args = parser.parse_args()

    if bool(args.place) == bool(args.bbox_from_sensors):
        print("ERROR: specify exactly one of --place or --bbox-from-sensors", file=sys.stderr)
        sys.exit(1)

    try:
        import osmnx
    except ImportError:
        print("ERROR: osmnx is not installed. Run: pip install -r backend/requirements.txt",
              file=sys.stderr)
        sys.exit(1)

    major_version = int(osmnx.__version__.split(".")[0])
    if major_version < 2:
        print(
            f"ERROR: this script requires OSMnx >= 2.0 (found {osmnx.__version__}). "
            f"It uses the 2.x graph_from_bbox(bbox=(west,south,east,north)) signature; "
            f"the 1.x north=/south=/east=/west= kwargs were removed in 2.0.0, so running "
            f"this script against 1.x will raise a TypeError, not silently misbehave. "
            f"Upgrade with: pip install 'osmnx==2.0.1'",
            file=sys.stderr,
        )
        sys.exit(1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if args.place:
            G, provenance = download_by_place(args.place, out_path, args.network_type)
        else:
            north, south, east, west = bbox_from_sensor_csv(args.bbox_from_sensors, args.buffer_km)
            G, provenance = download_by_bbox(north, south, east, west, out_path, args.network_type)
            provenance["buffer_km"] = args.buffer_km
            provenance["sensor_source_file"] = args.bbox_from_sensors
    except Exception as e:
        print(f"ERROR: OSM download failed: {e}", file=sys.stderr)
        print("This script does NOT fall back to synthetic/fake graph data. "
              "Fix connectivity/place-name/rate-limit issues and re-run.", file=sys.stderr)
        sys.exit(1)

    import osmnx as ox
    # Use the explicit io.save_graphml path rather than any bare ox.save_graphml
    # alias: the OSMnx 2.x docs consistently document save/load under the
    # `io` submodule, and I'm not relying on an unconfirmed top-level alias.
    ox.io.save_graphml(G, filepath=str(out_path))

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    metadata = {
        "classification": "REAL_GEOGRAPHIC",
        "source": "OpenStreetMap via OSMnx/Overpass API",
        "attribution": "(c) OpenStreetMap contributors, ODbL v1.0 - https://www.openstreetmap.org/copyright",
        "download_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "network_type": args.network_type,
        "node_count": n_nodes,
        "edge_count": n_edges,
        "provenance": provenance,
        "osmnx_version": __import__("osmnx").__version__,
    }
    meta_path = out_path.with_suffix(".meta.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[download_osm_network] Saved graph: {out_path} ({n_nodes} nodes, {n_edges} edges)")
    print(f"[download_osm_network] Saved metadata: {meta_path}")


if __name__ == "__main__":
    main()
