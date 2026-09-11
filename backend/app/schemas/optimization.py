from __future__ import annotations

from pydantic import BaseModel


class OptimizationStatus(BaseModel):
    default_iterations: int
    default_k_candidates: int
    solver: str = "simulated_annealing"
    solver_type: str = "quantum-inspired (classical hardware)"
    qubo_formulation: str = "candidate-route selection (exactly-one constraint)"
    default_weights: dict
