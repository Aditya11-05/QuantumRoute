"""
Road network loading.

Three sources of truth, in priority order when PROJECT_MODE=live:

1. A cached GraphML file on disk (fast, no network).
2. A fresh OSMnx download from OpenStreetMap/Overpass for
   settings.DEMO_REGION (slow, needs internet).
3. A deterministic *synthetic* grid road network, clearly labeled as
   synthetic, used automatically when PROJECT_MODE=demo or when (2)
   fails for any reason (no internet, Overpass down, etc).

IMPORTANT HONESTY NOTE:
The synthetic graph is NOT real OpenStreetMap data. It is a
deterministic grid of streets with randomized-but-seeded attributes
(lengths, speed limits, lane counts, one-way flags) meant to look and
behave like a small real town so the rest of the pipeline (routing,
traffic, ML, QUBO) can be built, run, and demoed without depending on
network access. Every place this graph is used, the API reports
`"graph_source": "synthetic"` vs `"graph_source": "osm"` so nothing is
silently misrepresented as real map data.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import networkx as nx

from app.config.settings import Settings, get_settings

logger = logging.getLogger("quantumroute.graph_loader")


@dataclass
class LoadedGraph:
    graph: nx.MultiDiGraph
    source: str  # "osm" | "osm_cache" | "synthetic"
    region: str


def _build_synthetic_graph(seed: int, rows: int = 9, cols: int = 9) -> nx.MultiDiGraph:
    """
    Build a deterministic synthetic road network shaped like a small grid
    town. This is explicitly NOT real map data — see module docstring.

    Node ids follow OSMnx conventions loosely: each node has 'x' (lon),
    'y' (lat). Edges carry the same attribute set OSMnx would give us
    (length, highway, maxspeed, lanes, name, oneway) so downstream code
    (baseline routing, cost function, ML features) does not need to know
    which source produced the graph.
    """
    rng = random.Random(seed)
    G = nx.MultiDiGraph()

    # Roughly center the synthetic grid near Kashipur, Uttarakhand
    # (29.21 N, 78.95 E) purely as a plausible demo anchor point.
    base_lat, base_lon = 29.2100, 78.9500
    lat_step = 0.0018   # ~200m per row
    lon_step = 0.0018   # ~200m per col

    highway_types = ["residential", "residential", "tertiary", "secondary"]
    speed_by_type = {
        "residential": 30,
        "tertiary": 40,
        "secondary": 50,
        "primary": 60,
    }

    node_id = lambda r, c: r * cols + c  # noqa: E731

    for r in range(rows):
        for c in range(cols):
            nid = node_id(r, c)
            G.add_node(
                nid,
                x=base_lon + c * lon_step + rng.uniform(-0.00005, 0.00005),
                y=base_lat + r * lat_step + rng.uniform(-0.00005, 0.00005),
                street_count=4,
            )

    # A handful of "primary" corridors (one horizontal, one vertical) to
    # make some routes clearly faster than others, like a real town has
    # arterial roads.
    primary_row = rows // 2
    primary_col = cols // 2

    def edge_attrs(r1, c1, r2, c2):
        if r1 == r2 and r1 == primary_row:
            highway = "primary"
        elif c1 == c2 and c1 == primary_col:
            highway = "primary"
        else:
            highway = rng.choice(highway_types)
        lanes = 3 if highway == "primary" else rng.choice([1, 1, 2])
        maxspeed = speed_by_type[highway]
        oneway = rng.random() < 0.12  # ~12% of segments are one-way
        return highway, lanes, maxspeed, oneway

    edge_id_counter = 0
    for r in range(rows):
        for c in range(cols):
            nid = node_id(r, c)
            neighbors = []
            if c + 1 < cols:
                neighbors.append((r, c + 1))
            if r + 1 < rows:
                neighbors.append((r + 1, c))
            for (nr, nc) in neighbors:
                nid2 = node_id(nr, nc)
                highway, lanes, maxspeed, oneway = edge_attrs(r, c, nr, nc)

                y1, x1 = G.nodes[nid]["y"], G.nodes[nid]["x"]
                y2, x2 = G.nodes[nid2]["y"], G.nodes[nid2]["x"]
                # Rough planar distance in meters (fine at this small scale).
                length_m = ((y2 - y1) * 111_320) ** 2 + (
                    (x2 - x1) * 111_320 * 0.87
                ) ** 2
                length_m = max(30.0, length_m ** 0.5)

                name = f"{'Grid' if highway != 'primary' else 'Main'} Street {r}-{c}"

                edge_id_counter += 1
                G.add_edge(
                    nid, nid2, key=0,
                    length=length_m,
                    highway=highway,
                    maxspeed=maxspeed,
                    lanes=lanes,
                    name=name,
                    oneway=oneway,
                    osmid=edge_id_counter,
                )
                if not oneway:
                    edge_id_counter += 1
                    G.add_edge(
                        nid2, nid, key=0,
                        length=length_m,
                        highway=highway,
                        maxspeed=maxspeed,
                        lanes=lanes,
                        name=name,
                        oneway=oneway,
                        osmid=edge_id_counter,
                    )

    G.graph["crs"] = "epsg:4326"
    G.graph["synthetic"] = True
    return G


def _try_load_cache(cache_path: Path) -> Optional[nx.MultiDiGraph]:
    if not cache_path.exists():
        return None
    try:
        G = nx.read_graphml(cache_path, node_type=int)
        # graphml stores everything as strings; osmnx has a loader for that,
        # but for our purposes we just coerce the numeric fields back.
        for _, _, data in G.edges(data=True):
            for k in ("length", "maxspeed", "lanes"):
                if k in data:
                    try:
                        data[k] = float(data[k])
                    except (TypeError, ValueError):
                        pass
        for _, data in G.nodes(data=True):
            for k in ("x", "y"):
                if k in data:
                    data[k] = float(data[k])
        logger.info("Loaded cached graph from %s", cache_path)
        return G
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read graph cache at %s: %s", cache_path, exc)
        return None


def _try_download_osm(region: str) -> Optional[nx.MultiDiGraph]:
    try:
        import osmnx as ox  # imported lazily; heavy + needs network
    except ImportError:
        logger.warning("osmnx not installed; cannot download live OSM graph")
        return None
    try:
        logger.info("Attempting live OSM download for region: %s", region)
        G = ox.graph_from_place(region, network_type="drive")
        return G
    except Exception as exc:  # noqa: BLE001
        # Network unavailable, Overpass timeout, region not found, etc.
        logger.warning("Live OSM download failed for '%s': %s", region, exc)
        return None


def load_graph(settings: Optional[Settings] = None, force_synthetic: bool = False) -> LoadedGraph:
    """
    Main entry point used by the rest of the app.

    Resolution order when PROJECT_MODE=live:
        cache -> live OSM download -> synthetic fallback (with a warning)

    When PROJECT_MODE=demo (or force_synthetic=True):
        synthetic graph is used directly, no network calls are made.
    """
    settings = settings or get_settings()
    cache_path = settings.resolved_path(settings.GRAPH_CACHE_PATH)

    if force_synthetic or settings.PROJECT_MODE == "demo":
        G = _build_synthetic_graph(seed=settings.DEMO_RANDOM_SEED)
        return LoadedGraph(graph=G, source="synthetic", region=settings.DEMO_REGION)

    cached = _try_load_cache(cache_path)
    if cached is not None:
        return LoadedGraph(graph=cached, source="osm_cache", region=settings.DEMO_REGION)

    downloaded = _try_download_osm(settings.DEMO_REGION)
    if downloaded is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            nx.write_graphml(downloaded, cache_path)
            logger.info("Cached freshly downloaded graph to %s", cache_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not write graph cache: %s", exc)
        return LoadedGraph(graph=downloaded, source="osm", region=settings.DEMO_REGION)

    logger.warning(
        "PROJECT_MODE=live but no cache and no network access to OSM; "
        "falling back to the synthetic demo graph. This is expected in "
        "sandboxed / offline environments."
    )
    G = _build_synthetic_graph(seed=settings.DEMO_RANDOM_SEED)
    return LoadedGraph(graph=G, source="synthetic", region=settings.DEMO_REGION)
