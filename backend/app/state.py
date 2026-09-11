"""
Process-wide singletons: the road graph and the ML predictor are
expensive to (re)build/load, so we load them once at FastAPI startup
and share them across requests via this module, rather than reloading
per-request.
"""
from __future__ import annotations

from typing import Optional

from app.config.settings import get_settings
from app.ml.predictor import CongestionPredictor
from app.routing.graph_loader import LoadedGraph, load_graph

_loaded_graph: Optional[LoadedGraph] = None
_predictor: Optional[CongestionPredictor] = None


def init_state() -> None:
    global _loaded_graph, _predictor
    settings = get_settings()
    _loaded_graph = load_graph(settings)
    model_path = str(settings.resolved_path(settings.MODEL_PATH))
    _predictor = CongestionPredictor(model_path)


def get_graph_state() -> LoadedGraph:
    if _loaded_graph is None:
        init_state()
    return _loaded_graph  # type: ignore[return-value]


def get_predictor() -> CongestionPredictor:
    if _predictor is None:
        init_state()
    return _predictor  # type: ignore[return-value]
