"""
Road network loading for QuantumRoute.

Project modes
-------------

demo
    Uses the deterministic synthetic Kashipur graph.
    This mode is intended for UI demonstrations and development.

research
    Uses the fixed OpenStreetMap GraphML prepared for the METR-LA
    research experiment.

    Research mode is deliberately fail-closed:
        - it does NOT download a different OSM graph;
        - it does NOT use the demo graph;
        - it does NOT silently fall back to synthetic data.

live
    Development mode using a cached OSM graph when available, followed
    by a live OSMnx/Overpass download.

The synthetic graph is therefore isolated from the research pipeline.
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
    """
    Container describing a loaded road network.

    source values:

        synthetic
            Deterministic demo graph.

        osm_cache
            Cached OSM graph used by live development mode.

        osm
            Fresh OSM graph downloaded by live development mode.

        osm_research
            Fixed OSM GraphML used by the controlled research experiment.
    """

    graph: nx.MultiDiGraph
    source: str
    region: str


class ResearchGraphError(RuntimeError):
    """Raised when the research road graph cannot be loaded safely."""


def _build_synthetic_graph(
    seed: int,
    rows: int = 9,
    cols: int = 9,
) -> nx.MultiDiGraph:
    """
    Build a deterministic synthetic road network.

    This graph is explicitly NOT real OpenStreetMap data.

    It exists only for:
        - demo mode
        - local development
        - deterministic UI demonstrations
        - tests that explicitly require synthetic data
    """

    rng = random.Random(seed)
    G = nx.MultiDiGraph()

    # Roughly center the synthetic grid near Kashipur, Uttarakhand.
    base_lat, base_lon = 29.2100, 78.9500

    lat_step = 0.0018
    lon_step = 0.0018

    highway_types = [
        "residential",
        "residential",
        "tertiary",
        "secondary",
    ]

    speed_by_type = {
        "residential": 30,
        "tertiary": 40,
        "secondary": 50,
        "primary": 60,
    }

    node_id = lambda r, c: r * cols + c

    for r in range(rows):
        for c in range(cols):
            nid = node_id(r, c)

            G.add_node(
                nid,
                x=base_lon
                + c * lon_step
                + rng.uniform(-0.00005, 0.00005),
                y=base_lat
                + r * lat_step
                + rng.uniform(-0.00005, 0.00005),
                street_count=4,
            )

    primary_row = rows // 2
    primary_col = cols // 2

    def edge_attrs(r1, c1, r2, c2):
        if r1 == r2 and r1 == primary_row:
            highway = "primary"
        elif c1 == c2 and c1 == primary_col:
            highway = "primary"
        else:
            highway = rng.choice(highway_types)

        lanes = (
            3
            if highway == "primary"
            else rng.choice([1, 1, 2])
        )

        maxspeed = speed_by_type[highway]
        oneway = rng.random() < 0.12

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

            for nr, nc in neighbors:
                nid2 = node_id(nr, nc)

                highway, lanes, maxspeed, oneway = edge_attrs(
                    r,
                    c,
                    nr,
                    nc,
                )

                y1 = G.nodes[nid]["y"]
                x1 = G.nodes[nid]["x"]

                y2 = G.nodes[nid2]["y"]
                x2 = G.nodes[nid2]["x"]

                length_m = (
                    ((y2 - y1) * 111_320) ** 2
                    + ((x2 - x1) * 111_320 * 0.87) ** 2
                )

                length_m = max(
                    30.0,
                    length_m ** 0.5,
                )

                name = (
                    f"{'Grid' if highway != 'primary' else 'Main'} "
                    f"Street {r}-{c}"
                )

                edge_id_counter += 1

                G.add_edge(
                    nid,
                    nid2,
                    key=0,
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
                        nid2,
                        nid,
                        key=0,
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
    G.graph["data_provenance"] = "SYNTHETIC"

    return G


def _coerce_graphml_attributes(
    G: nx.MultiDiGraph,
) -> nx.MultiDiGraph:
    """
    Convert GraphML string attributes back to useful numeric values.

    Important:
        maxspeed is deliberately NOT converted to float here.

    OSM maxspeed values can contain strings such as:
        "35 mph"
        "25 mph"
        "['35 mph', '30 mph']"

    Parsing maxspeed belongs to the dedicated speed-estimation layer.
    """

    for _, _, data in G.edges(data=True):
        if "length" in data:
            try:
                data["length"] = float(data["length"])
            except (TypeError, ValueError):
                pass

        if "lanes" in data:
            value = data["lanes"]

            try:
                data["lanes"] = float(value)
            except (TypeError, ValueError):
                # Keep complex/list-like OSM values untouched.
                pass

    for _, data in G.nodes(data=True):
        for key in ("x", "y"):
            if key in data:
                try:
                    data[key] = float(data[key])
                except (TypeError, ValueError):
                    pass

    return G


def _try_load_graphml(
    graph_path: Path,
) -> Optional[nx.MultiDiGraph]:
    """
    Load an OSM GraphML file.

    Returns None for ordinary loading failures.

    Research mode wraps this with a fail-closed error so the caller
    receives an explicit failure rather than a synthetic fallback.
    """

    if not graph_path.exists():
        logger.error(
            "GraphML file does not exist: %s",
            graph_path,
        )
        return None

    try:
        G = nx.read_graphml(
            graph_path,
            node_type=int,
        )

        G = _coerce_graphml_attributes(G)

        logger.info(
            "Loaded GraphML road network from %s",
            graph_path,
        )

        return G

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to load GraphML file %s: %s",
            graph_path,
            exc,
        )
        return None


def _try_load_cache(
    cache_path: Path,
) -> Optional[nx.MultiDiGraph]:
    """
    Load the development/live OSM cache.

    This function is intentionally NOT used by research mode.
    """

    return _try_load_graphml(cache_path)


def _try_download_osm(
    region: str,
) -> Optional[nx.MultiDiGraph]:
    """
    Download an OSM road network for live development mode.

    This function is intentionally NOT used by research mode.
    """

    try:
        import osmnx as ox
    except ImportError:
        logger.warning(
            "osmnx is not installed; cannot download live OSM graph"
        )
        return None

    try:
        logger.info(
            "Attempting live OSM download for region: %s",
            region,
        )

        G = ox.graph_from_place(
            region,
            network_type="drive",
        )

        G.graph["data_provenance"] = "REAL_GEOGRAPHIC"

        return G

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Live OSM download failed for '%s': %s",
            region,
            exc,
        )
        return None


def _load_research_graph(
    settings: Settings,
) -> LoadedGraph:
    """
    Load the fixed research road network.

    Research mode is fail-closed.

    There is intentionally:
        - no live OSM download;
        - no cache fallback;
        - no synthetic fallback.
    """

    graph_path = settings.resolved_path(
        settings.RESEARCH_GRAPH_PATH
    )

    if not graph_path.exists():
        raise ResearchGraphError(
            "Research road graph is missing.\n"
            f"Expected: {graph_path}\n"
            "Research mode requires the fixed METR-LA OSM "
            "GraphML artifact."
        )

    G = _try_load_graphml(graph_path)

    if G is None:
        raise ResearchGraphError(
            "Research road graph could not be loaded.\n"
            f"GraphML: {graph_path}\n"
            "Research mode refuses to fall back to synthetic "
            "or live data."
        )

    # Explicit provenance marker.
    G.graph["data_provenance"] = "REAL_GEOGRAPHIC"
    G.graph["research_graph"] = True
    G.graph["synthetic"] = False

    return LoadedGraph(
        graph=G,
        source="osm_research",
        region="METR-LA sensor footprint",
    )


def load_graph(
    settings: Optional[Settings] = None,
    force_synthetic: bool = False,
) -> LoadedGraph:
    """
    Main road-network loading entry point.

    Mode behavior
    -------------

    demo:
        synthetic graph only.

    research:
        fixed METR-LA OSM GraphML only.
        Missing/corrupt graph -> ResearchGraphError.

    live:
        cache -> live OSM download -> synthetic fallback.

    force_synthetic:
        Explicitly forces the deterministic demo graph regardless of
        PROJECT_MODE. This should only be used by tests/demo tooling.
    """

    settings = settings or get_settings()

    # --------------------------------------------------------------
    # Explicit synthetic override
    # --------------------------------------------------------------

    if force_synthetic:
        G = _build_synthetic_graph(
            seed=settings.DEMO_RANDOM_SEED
        )

        return LoadedGraph(
            graph=G,
            source="synthetic",
            region=settings.DEMO_REGION,
        )

    # --------------------------------------------------------------
    # DEMO MODE
    # --------------------------------------------------------------

    if settings.PROJECT_MODE == "demo":
        G = _build_synthetic_graph(
            seed=settings.DEMO_RANDOM_SEED
        )

        return LoadedGraph(
            graph=G,
            source="synthetic",
            region=settings.DEMO_REGION,
        )

    # --------------------------------------------------------------
    # RESEARCH MODE
    # --------------------------------------------------------------

    if settings.PROJECT_MODE == "research":
        return _load_research_graph(settings)

    # --------------------------------------------------------------
    # LIVE DEVELOPMENT MODE
    # --------------------------------------------------------------

    if settings.PROJECT_MODE == "live":
        cache_path = settings.resolved_path(
            settings.GRAPH_CACHE_PATH
        )

        cached = _try_load_cache(cache_path)

        if cached is not None:
            cached.graph["data_provenance"] = (
                "REAL_GEOGRAPHIC"
            )

            return LoadedGraph(
                graph=cached,
                source="osm_cache",
                region=settings.DEMO_REGION,
            )

        downloaded = _try_download_osm(
            settings.DEMO_REGION
        )

        if downloaded is not None:
            try:
                cache_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                nx.write_graphml(
                    downloaded,
                    cache_path,
                )

                logger.info(
                    "Cached freshly downloaded graph to %s",
                    cache_path,
                )

            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Could not write graph cache: %s",
                    exc,
                )

            return LoadedGraph(
                graph=downloaded,
                source="osm",
                region=settings.DEMO_REGION,
            )

        # This fallback remains ONLY for live development mode.
        logger.warning(
            "PROJECT_MODE=live but no cache and no network "
            "access to OSM. Falling back to the synthetic "
            "demo graph for development."
        )

        G = _build_synthetic_graph(
            seed=settings.DEMO_RANDOM_SEED
        )

        return LoadedGraph(
            graph=G,
            source="synthetic",
            region=settings.DEMO_REGION,
        )

    # The Settings validator should make this unreachable.
    raise ValueError(
        f"Unsupported PROJECT_MODE: {settings.PROJECT_MODE}"
    )