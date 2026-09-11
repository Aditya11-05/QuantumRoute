#!/usr/bin/env python3
"""
scripts/download_osm_data.py

Attempts to download the real road network for settings.DEMO_REGION
from OpenStreetMap via OSMnx, and caches it to GRAPH_CACHE_PATH.

Usage:
    cd backend
    python ../scripts/download_osm_data.py
    python ../scripts/download_osm_data.py --region "Kashipur, Uttarakhand, India"
    python ../scripts/download_osm_data.py --force-synthetic

If there is no internet access (or Overpass is unreachable), this
script will clearly report that and tell you demo mode will be used
instead - it will NOT silently pretend to have downloaded real data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config.settings import get_settings, Settings  # noqa: E402
from app.routing.graph_loader import load_graph  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Download/cache the QuantumRoute road network")
    parser.add_argument("--region", type=str, default=None, help="Override DEMO_REGION, e.g. 'Kashipur, Uttarakhand, India'")
    parser.add_argument("--force-synthetic", action="store_true", help="Skip OSM entirely and (re)generate the synthetic demo graph")
    args = parser.parse_args()

    settings = get_settings()
    if args.region:
        settings = Settings(**{**settings.model_dump(), "DEMO_REGION": args.region, "PROJECT_MODE": "live"})
    elif not args.force_synthetic:
        settings = Settings(**{**settings.model_dump(), "PROJECT_MODE": "live"})

    print(f"Region: {settings.DEMO_REGION}")
    print(f"Cache path: {settings.resolved_path(settings.GRAPH_CACHE_PATH)}")

    result = load_graph(settings, force_synthetic=args.force_synthetic)

    print(f"\nGraph source: {result.source}")
    print(f"Nodes: {result.graph.number_of_nodes()}")
    print(f"Edges: {result.graph.number_of_edges()}")

    if result.source == "synthetic":
        print(
            "\nNOTE: A synthetic demo graph was used instead of real OpenStreetMap "
            "data. This happens when PROJECT_MODE=demo, or when live OSM/Overpass "
            "servers were unreachable (no internet, firewall, or rate limiting). "
            "This is expected and fine for offline SIH demos."
        )
    else:
        print("\nReal OpenStreetMap data was downloaded and cached successfully.")


if __name__ == "__main__":
    main()
