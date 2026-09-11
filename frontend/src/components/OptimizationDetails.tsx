import ConvergenceChart from "../charts/ConvergenceChart";
import type { OptimizeRouteResponse } from "../types/api";

interface OptimizationDetailsProps {
  result: OptimizeRouteResponse | null;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-[var(--qr-text-muted)]">{label}</div>
      <div className="font-mono-qr text-sm text-[var(--qr-text)]">{value}</div>
    </div>
  );
}

export default function OptimizationDetails({ result }: OptimizationDetailsProps) {
  if (!result || !result.found) {
    return (
      <p className="text-sm text-[var(--qr-text-muted)]">
        Run an optimization to see QUBO and solver details here.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <Stat label="QUBO size (variables)" value={String(result.qubo_size)} />
        <Stat label="Penalty coefficient" value={result.qubo_penalty.toFixed(3)} />
        <Stat label="Solver iterations" value={result.solver_iterations.toLocaleString()} />
        <Stat label="Solver runtime" value={`${result.solver_runtime_ms.toFixed(2)} ms`} />
        <Stat label="Best energy" value={result.solver_best_energy.toFixed(4)} />
        <Stat label="Pipeline total" value={`${result.total_pipeline_time_ms.toFixed(2)} ms`} />
      </div>

      {result.was_repaired && (
        <div className="text-xs rounded border border-[var(--qr-amber)]/40 bg-[var(--qr-amber)]/10 text-[var(--qr-amber)] px-2 py-1.5">
          The raw annealer output violated the "exactly one route" constraint and was deterministically
          repaired to the cheapest selected/available route.
        </div>
      )}

      <div>
        <div className="text-[10px] uppercase tracking-wide text-[var(--qr-text-muted)] mb-1">
          Optimizer convergence (best energy so far)
        </div>
        <ConvergenceChart history={result.solver_convergence_history} />
      </div>

      <div className="text-xs rounded border border-[var(--qr-border)] bg-[var(--qr-panel)] px-3 py-2 text-[var(--qr-text-muted)] leading-relaxed">
        {result.quantum_disclaimer}
      </div>
    </div>
  );
}
