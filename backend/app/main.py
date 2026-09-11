from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import benchmark, optimization, routing, system, traffic
from app.config.settings import get_settings
from app.state import init_state

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "QuantumRoute - intelligent, multi-objective, traffic-aware route "
        "optimization prototype (SIH260137). Combines OpenStreetMap road "
        "graphs, ML congestion prediction, QUBO formulation, and "
        "quantum-inspired (classical) simulated annealing. "
        "See /system/status for graph_source, ml_model_loaded, and mode."
    ),
)

# ---------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------
# Frontend is running on http://localhost:5174
# Backend is running on http://localhost:8000
#
# Explicitly allow the frontend origin so browser requests
# to the FastAPI API are not blocked by CORS.
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# STARTUP
# ---------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    init_state()


# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------

app.include_router(system.router)
app.include_router(routing.router)
app.include_router(traffic.router)
app.include_router(optimization.router)
app.include_router(benchmark.router)