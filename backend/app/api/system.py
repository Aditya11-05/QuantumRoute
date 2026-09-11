from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings
from app.routing.node_utils import bounding_box
from app.schemas.routing import RegionInfo
from app.state import get_graph_state, get_predictor

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/system/status")
def system_status():
    settings = get_settings()
    lg = get_graph_state()
    predictor = get_predictor()
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "project_mode": settings.PROJECT_MODE,
        "graph_source": lg.source,
        "region": lg.region,
        "num_nodes": lg.graph.number_of_nodes(),
        "num_edges": lg.graph.number_of_edges(),
        "ml_model_loaded": predictor.is_ready,
        "ml_model_load_error": predictor.load_error,
        "quantum_disclaimer": (
            "Optimization uses quantum-inspired simulated annealing on "
            "classical hardware - no quantum computer is used."
        ),
    }


@router.get("/map/regions", response_model=list[RegionInfo])
def map_regions():
    lg = get_graph_state()
    return [
        RegionInfo(
            name=lg.region,
            graph_source=lg.source,
            num_nodes=lg.graph.number_of_nodes(),
            num_edges=lg.graph.number_of_edges(),
            bounding_box=bounding_box(lg.graph),
        )
    ]
