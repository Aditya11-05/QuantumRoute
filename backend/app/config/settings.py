"""
Centralized configuration for QuantumRoute.

All tunable values (region, weights, iteration counts, paths) live here
and are sourced from environment variables / a .env file rather than
being hardcoded throughout the codebase.

Project modes:

    demo
        Deterministic synthetic Kashipur demo. No external traffic data
        is used.

    research
        Reproducible research mode using the fixed METR-LA historical
        traffic dataset and the corresponding OpenStreetMap road graph.
        Research mode must fail closed if required real-data artifacts
        are missing.

    live
        Development mode using cached/live OpenStreetMap data. This mode
        is separate from the controlled research experiment.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
# .../QuantumRoute_project/backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    APP_NAME: str = "QuantumRoute"
    APP_VERSION: str = "0.1.0"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ------------------------------------------------------------------
    # Project mode
    # ------------------------------------------------------------------
    #
    # demo:
    #     Deterministic synthetic Kashipur demonstration.
    #
    # research:
    #     Fixed METR-LA + OSM research experiment.
    #
    # live:
    #     Development mode with cached/live OSM.
    #
    PROJECT_MODE: str = "demo"

    # ------------------------------------------------------------------
    # Frontend / API
    # ------------------------------------------------------------------

    CORS_ORIGINS: str = "http://localhost:5173"

    # ------------------------------------------------------------------
    # Demo configuration
    # ------------------------------------------------------------------

    DEMO_REGION: str = "Kashipur, Uttarakhand, India"

    GRAPH_CACHE_PATH: str = "../data/osm/graph_cache.graphml"

    MODEL_PATH: str = "../data/models/congestion_model.txt"

    DEMO_RANDOM_SEED: int = 42

    # ------------------------------------------------------------------
    # Research data
    # ------------------------------------------------------------------
    #
    # These paths point to fixed, locally downloaded research artifacts.
    #
    # They are deliberately separate from GRAPH_CACHE_PATH and MODEL_PATH
    # so research mode cannot accidentally use the synthetic/demo assets.
    #

    # OpenStreetMap road graph covering the METR-LA sensor footprint.
    RESEARCH_GRAPH_PATH: str = (
        "../data/raw/osm/metr_la_network.graphml"
    )

    # METR-LA historical traffic-speed observations.
    RESEARCH_TRAFFIC_PATH: str = (
        "../data/raw/metr-la.h5"
    )

    # Sensor -> directed OSM edge mapping.
    RESEARCH_SENSOR_MAPPING_PATH: str = (
        "../data/processed/metr_la_sensor_edge_mapping.csv"
    )

    # Sensor-specific reference speeds calculated using ONLY the
    # chronological training split.
    RESEARCH_REFERENCE_SPEED_PATH: str = (
        "../data/processed/metr_la_reference_speeds_train.csv"
    )

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    OPTIMIZATION_ITERATIONS: int = 2000

    # ------------------------------------------------------------------
    # Multi-objective routing weights
    # ------------------------------------------------------------------

    WEIGHT_TRAVEL_TIME: float = 0.35
    WEIGHT_CONGESTION: float = 0.30
    WEIGHT_DISTANCE: float = 0.15
    WEIGHT_FUEL: float = 0.10
    WEIGHT_INTERSECTION: float = 0.05
    WEIGHT_INCIDENT: float = 0.05

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @field_validator("PROJECT_MODE")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        """
        Validate the execution mode.

        Research is intentionally an explicit mode rather than being
        treated as a variant of live/demo operation.
        """
        v = v.lower().strip()

        if v not in {"demo", "research", "live"}:
            raise ValueError(
                "PROJECT_MODE must be 'demo', 'research', or 'live'"
            )

        return v

    # ------------------------------------------------------------------
    # Derived configuration
    # ------------------------------------------------------------------

    @property
    def cors_origins_list(self) -> List[str]:
        """Return configured CORS origins as a cleaned list."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def default_weights(self) -> dict:
        """Return the configured multi-objective routing weights."""
        return {
            "travel_time": self.WEIGHT_TRAVEL_TIME,
            "congestion": self.WEIGHT_CONGESTION,
            "distance": self.WEIGHT_DISTANCE,
            "fuel": self.WEIGHT_FUEL,
            "intersection": self.WEIGHT_INTERSECTION,
            "incident": self.WEIGHT_INCIDENT,
        }

    def resolved_path(self, relative: str) -> Path:
        """
        Resolve a configured path relative to the project root.

        BACKEND_DIR is:
            .../QuantumRoute_project/backend

        Therefore a path such as:
            ../data/raw/metr-la.h5

        resolves to:
            .../QuantumRoute_project/data/raw/metr-la.h5
        """
        path = Path(relative)

        if path.is_absolute():
            return path

        return (BACKEND_DIR / path).resolve()


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
