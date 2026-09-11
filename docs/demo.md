# SIH Demonstration Script (3–5 minutes)

## Before you demo

Run `python scripts/setup_demo.py` from the project root the night
before — it trains the model, generates traffic snapshots, runs a
pipeline sanity check, and runs the full test suite, so you know
everything works before you're in front of judges. Keep
`PROJECT_MODE=demo` set in `backend/.env` for a fully offline-safe
demo (no dependency on venue WiFi).

## Script

**1. Open the dashboard** (`npm run dev` in `frontend/`, backend
already running). Point out the top bar: mode, graph source, node/edge
counts, ML status — this is live telemetry, not decoration.

**2. Select source and destination** by clicking the map. Mention:
"This is a synthetic demo road network for Kashipur — see
docs/limitations.md for why, in one sentence: no free live-traffic API
for a small town, so we built a transparent, seeded simulator instead."

**3. Show the baseline route** — click "Optimize route" with traffic
scenario = **Low**. Point at the comparison table: Dijkstra and A*
agree exactly (this is the A* admissibility proof, made visible).

**4. Switch to Heavy or Peak traffic.** Click Optimize again. Show the
route/ETA/congestion numbers changing — this proves traffic is
actually being recalculated, not a canned animation.

**5. Show Dijkstra vs A* vs QuantumRoute** in the comparison table.
Be ready for: "QuantumRoute usually ties, not beats, the baselines on
cost — here's why" (see docs/optimization.md's honest framing;
mention the multi-vehicle/constraint extension as the real value prop
if asked "so what's the point").

**6. Show the AI Prediction panel.** Drag the hour slider from 3am to
8am — the predicted congestion jumps, live, because the LightGBM model
genuinely learned the rush-hour pattern from data (not hardcoded).

**7. Show Optimization Details.** QUBO size, penalty, solver
iterations/runtime, best energy, and the convergence chart — point out
the chart is monotonically improving (best-so-far), which is real
annealing behavior, not a smoothed illustration.

**8. Close with the innovation framing** (see docs/optimization.md):
"The point isn't beating Dijkstra on a single-vehicle shortest path —
Dijkstra is already optimal there. The point is a working, correct,
end-to-end QUBO/quantum-inspired pipeline whose formulation extends
naturally to problems classical single-path search can't express
directly, like multi-vehicle routing with shared road capacity."

## Reliability notes

- Traffic simulation and the annealer are **seeded** — the same
  scenario + seed always reproduces the same numbers, so the demo is
  repeatable and won't surprise you on stage.
- If the WiFi is unreliable, this is not a problem: `PROJECT_MODE=demo`
  never makes a network call.
- Have `data/models/training_report.json` and
  `data/benchmarks/benchmark_results.json` open in a second tab as
  backup evidence if projector/live-demo issues arise.
