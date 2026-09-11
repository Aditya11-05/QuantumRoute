from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings
from app.schemas.optimization import OptimizationStatus

router = APIRouter(tags=["optimization"])


@router.get("/optimization/status", response_model=OptimizationStatus)
def optimization_status():
    settings = get_settings()
    return OptimizationStatus(
        default_iterations=settings.OPTIMIZATION_ITERATIONS,
        default_k_candidates=5,
        default_weights=settings.default_weights,
    )


@router.get("/model/info")
def model_info():
    import json
    from pathlib import Path

    settings = get_settings()
    report_path = settings.resolved_path("../data/models/training_report.json")
    if not Path(report_path).exists():
        return {
            "trained": False,
            "message": "No training report found. Run scripts/train_model.py first.",
        }
    with open(report_path) as f:
        report = json.load(f)
    return {"trained": True, **report}
