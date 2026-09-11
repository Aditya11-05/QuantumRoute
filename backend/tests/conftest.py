"""
Shared pytest fixtures. Deliberately does NOT touch live OpenStreetMap
servers - all graph fixtures use the deterministic synthetic generator
so unit tests are fast, offline, and reproducible in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.routing.graph_loader import load_graph  # noqa: E402
from app.config.settings import Settings  # noqa: E402


@pytest.fixture(scope="session")
def synthetic_graph():
    settings = Settings(PROJECT_MODE="demo", DEMO_RANDOM_SEED=42)
    return load_graph(settings, force_synthetic=True).graph


@pytest.fixture(scope="session")
def graph_source_target(synthetic_graph):
    nodes = list(synthetic_graph.nodes)
    return nodes[0], nodes[-1]
