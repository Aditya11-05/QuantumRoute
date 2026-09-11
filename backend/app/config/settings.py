"""
Centralized configuration for QuantumRoute.

All tunable values (region, weights, iteration counts, paths) live here
and are sourced from environment variables / a .env file rather than
being hardcoded throughout the codebase. This is what lets the same
code run in PROJECT_MODE=demo (offline, synthetic data, deterministic)
or PROJECT_MODE=live (real OSM download, live-ish traffic feed hook).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "QuantumRoute"
    APP_VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # "demo" -> never touch the network, use synthetic/cached graph + traffic.
    # "live" -> attempt OSMnx download from OpenStreetMap/Overpass; falls
    # back to demo mode automatically if that fails (see graph_loader.py).
    PROJECT_MODE: str = "demo"

    CORS_ORIGINS: str = "http://localhost:5173"

    DEMO_REGION: str = "Kashipur, Uttarakhand, India"
    GRAPH_CACHE_PATH: str = "../data/osm/graph_cache.graphml"
    MODEL_PATH: str = "../data/models/congestion_model.txt"

    OPTIMIZATION_ITERATIONS: int = 2000

    WEIGHT_TRAVEL_TIME: float = 0.35
    WEIGHT_CONGESTION: float = 0.30
    WEIGHT_DISTANCE: float = 0.15
    WEIGHT_FUEL: float = 0.10
    WEIGHT_INTERSECTION: float = 0.05
    WEIGHT_INCIDENT: float = 0.05

    DEMO_RANDOM_SEED: int = 42

    @field_validator("PROJECT_MODE")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"demo", "live"}:
            raise ValueError("PROJECT_MODE must be 'demo' or 'live'")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def default_weights(self) -> dict:
        return {
            "travel_time": self.WEIGHT_TRAVEL_TIME,
            "congestion": self.WEIGHT_CONGESTION,
            "distance": self.WEIGHT_DISTANCE,
            "fuel": self.WEIGHT_FUEL,
            "intersection": self.WEIGHT_INTERSECTION,
            "incident": self.WEIGHT_INCIDENT,
        }

    def resolved_path(self, relative: str) -> Path:
        """Resolve a path relative to the backend/ directory."""
        p = Path(relative)
        if p.is_absolute():
            return p
        return (BACKEND_DIR / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
