# QuantumRoute

**Smart India Hackathon 2026 — Problem Statement SIH260137**

Intelligent, multi-objective, traffic-aware route optimization
prototype combining OpenStreetMap road graphs, a real trained ML
congestion model, a genuine QUBO formulation, and a quantum-inspired
(classical) simulated-annealing solver.

**Technical question this project explores:** *Can quantum-inspired
and metaheuristic optimization improve multi-objective route selection
under dynamic traffic conditions compared with conventional
shortest-path algorithms?* Our honest, measured answer (see
[docs/benchmarking.md](docs/benchmarking.md) and
[docs/optimization.md](docs/optimization.md)) is: **not on cost, for a
single-vehicle single-path problem — QuantumRoute ties but does not
beat Dijkstra there, and is slower.** The real value of the QUBO/
annealing pipeline built here is architectural: it generalizes to
multi-vehicle, multi-constraint routing problems that classical
single-path search cannot express directly. We say this plainly
because an honest, defensible "no, but here's why it still matters" is
worth more in front of judges than an inflated claim.

This is **not** a competitor to Google/Apple Maps. It is a research
prototype.

---

## What's real vs. simulated (read this first)

| Component | Status |
|---|---|
| Road network | Real OSMnx/OpenStreetMap code path exists (`PROJECT_MODE=live`), but **could not be tested in the sandboxed environment this was built in** (no network egress to OSM/Overpass servers there). Falls back automatically to a deterministic **synthetic** road graph, clearly labeled `graph_source: "synthetic"` everywhere. **Test live mode yourself** before relying on it. |
| Traffic | 100% synthetic, seeded, deterministic simulator. Not a live feed. |
| ML model | Really trained (LightGBM), real held-out metrics (MAE/RMSE/R²), but trained on a synthetic dataset — see [docs/ml_model.md](docs/ml_model.md). |
| QUBO | Real math, real Q matrix, verified against brute-force enumeration — see [docs/qubo.md](docs/qubo.md). |
| "Quantum" optimization | Simulated annealing — classical CPU, quantum-inspired only. **No quantum hardware anywhere.** |
| Benchmarks | Real numbers from actually running the algorithms — see [docs/benchmarking.md](docs/benchmarking.md). |

Full limitations list: [docs/limitations.md](docs/limitations.md).

---

## Architecture

```
React Dashboard (Vite/TS/Leaflet) ──HTTP/JSON──► FastAPI Backend
                                                       │
                             OSM graph (or synthetic) ─┤
                             Synthetic traffic ─────────┤
                             LightGBM congestion model ─┤
                             Multi-objective cost fn ───┤
                             Dijkstra + A* baselines ───┤
                             Yen's k-shortest candidates┤
                             QUBO (route selection) ────┤
                             Simulated annealing solver ┤
                             Benchmarking ──────────────┘
```

Full detail: [docs/architecture.md](docs/architecture.md).

---

## Prerequisites

- Python 3.10+ (developed/tested with 3.12.3)
- Node.js 18+ (developed/tested with v22.22.2) and npm

Check your versions:
```bash
python3 --version
node --version
npm --version
```

---

## Installation

```bash
git clone <your-repo-url> QuantumRoute
cd QuantumRoute

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # defaults to PROJECT_MODE=demo (offline-safe)

# Frontend
cd ../frontend
npm install
cp .env.example .env               # points at http://localhost:8000 by default
```

---

## One-shot setup (recommended before your first run or before a demo)

```bash
cd QuantumRoute
python3 scripts/setup_demo.py
```
This trains the ML model, generates reference traffic snapshots, runs
an end-to-end pipeline sanity check, and runs the full backend test
suite — so you know the system works before you're on stage.

---

## Running the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Health check: http://localhost:8000/health
- Swagger/OpenAPI docs: http://localhost:8000/docs
- System status (graph source, ML status, mode): http://localhost:8000/system/status

## Running the frontend

```bash
cd frontend
npm run dev
```
Open the printed local URL (typically http://localhost:5173).

---

## Training the ML model

```bash
cd QuantumRoute
python3 scripts/train_model.py
# or with custom sample size/seed:
python3 scripts/train_model.py --n-samples 10000 --seed 7
```
Saves the model to `data/models/congestion_model.txt` and a real
evaluation report to `data/models/training_report.json`. See
[docs/ml_model.md](docs/ml_model.md) for what the reported metrics
actually mean.

## Loading / downloading road network data

```bash
cd QuantumRoute
python3 scripts/download_osm_data.py                        # uses .env's DEMO_REGION, tries live OSM
python3 scripts/download_osm_data.py --region "Your City, State, Country"
python3 scripts/download_osm_data.py --force-synthetic       # skip OSM entirely
```
If OSM/Overpass is unreachable (no internet, firewall, rate limit),
this **clearly reports that** and falls back to the synthetic demo
graph — it will not silently pretend to have real data.

## Generating synthetic traffic snapshots (optional — the API also generates traffic on the fly)

```bash
cd QuantumRoute
python3 scripts/generate_traffic_data.py
```

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```
65 tests (unit + integration), all offline — no live-network
dependency. Verified passing at the time this project was built.

## Running the benchmark suite

```bash
cd QuantumRoute
python3 scripts/benchmark.py --pairs 5 --iterations 2000 --seed 42
```
Saves results to `data/benchmarks/benchmark_results.json`. See
[docs/benchmarking.md](docs/benchmarking.md) for real measured numbers
and their honest interpretation.

---

## Demo

See [docs/demo.md](docs/demo.md) for a reliable, reproducible 3–5
minute SIH demonstration script.

---

## Documentation index

| Doc | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System design and module map |
| [docs/algorithms.md](docs/algorithms.md) | Dijkstra, A*, Yen's — math and verification |
| [docs/ml_model.md](docs/ml_model.md) | Model choice, features, real training metrics |
| [docs/qubo.md](docs/qubo.md) | Full QUBO mathematical formulation |
| [docs/optimization.md](docs/optimization.md) | Cost function, simulated annealing, honest results |
| [docs/benchmarking.md](docs/benchmarking.md) | Methodology and real measured numbers |
| [docs/demo.md](docs/demo.md) | SIH demonstration script |
| [docs/terminology.md](docs/terminology.md) | Every required term, explained 5 ways |
| [docs/limitations.md](docs/limitations.md) | Everything this project does NOT do |

---

## Troubleshooting

**`ModuleNotFoundError` when running scripts** — make sure you
activated the virtualenv (`source backend/.venv/bin/activate`) and are
running scripts from the paths shown above (they resolve imports
relative to `backend/`).

**`/route/optimize` returns `found: false`** — likely means the
selected traffic scenario (e.g. `closure`) disconnected the source from
the destination in the demo graph. Try a different scenario or a
different source/destination pair.

**Frontend shows "backend unreachable"** — confirm the backend is
running on the port your frontend's `VITE_API_BASE_URL` points to
(default `http://localhost:8000`), and check for CORS errors in the
browser console (adjust `CORS_ORIGINS` in `backend/.env` if your
frontend runs on a different port).

**`PROJECT_MODE=live` doesn't download real OSM data** — this exact
failure mode was hit and documented during development (no network
egress in that sandbox). On a normal machine with internet access this
should work via OSMnx, but **please verify it yourself** — see
[docs/limitations.md](docs/limitations.md) item 3.

**LightGBM install issues on some platforms** — LightGBM occasionally
needs `libomp` (macOS: `brew install libomp`). If problems persist,
delete `.venv` and reinstall.

---

## License / attribution

Built for Smart India Hackathon 2026. Road network data, when running
in live mode, is © OpenStreetMap contributors, available under the
Open Database License.
