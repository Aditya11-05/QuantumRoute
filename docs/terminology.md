# Terminology

Each term: **Simple** · **Technical** · **Analogy** · **QuantumRoute example** · **Why we use it**

---

### Graph
- **Simple:** dots connected by lines.
- **Technical:** a set of nodes (vertices) and edges representing pairwise relationships.
- **Analogy:** a subway map — stations and the lines between them.
- **QuantumRoute:** the road network is a graph; intersections are nodes, road segments are edges.
- **Why:** graphs are the natural representation for anything with "places" and "connections between places."

### Node
- **Simple:** a point/dot in a graph.
- **Technical:** a graph vertex, may carry attributes (here: lat/lon).
- **Analogy:** a subway station.
- **QuantumRoute:** an intersection or road endpoint (`G.nodes[id]["x"], ["y"]`).
- **Why:** the atomic unit routing algorithms move between.

### Edge
- **Simple:** a line connecting two dots.
- **Technical:** a graph connection, may be directed/weighted, carries attributes.
- **Analogy:** the subway track between two stations.
- **QuantumRoute:** a road segment, carrying `length`, `highway`, `maxspeed`, `lanes`.
- **Why:** the cost function is evaluated per edge.

### Directed graph
- **Simple:** connections that only go one way.
- **Technical:** edges are ordered pairs (u→v); (u→v) existing doesn't imply (v→u) exists.
- **Analogy:** a one-way street.
- **QuantumRoute:** our graph is a `MultiDiGraph` — ~12% of synthetic edges are one-way, matching real cities.
- **Why:** real road networks have one-way streets; an undirected graph would produce illegal routes.

### Weighted graph
- **Simple:** connections have "costs" attached.
- **Technical:** edges carry a numeric weight used by shortest-path algorithms.
- **Analogy:** toll amounts on different highway segments.
- **QuantumRoute:** edge weight = the dynamic multi-objective cost (`compute_edge_cost`), not just distance.
- **Why:** lets Dijkstra/A* optimize for something richer than raw distance.

### Shortest path
- **Simple:** the cheapest way from A to B.
- **Technical:** the path minimizing total edge weight from source to target.
- **Analogy:** the fastest subway route between two stations.
- **QuantumRoute:** what Dijkstra/A* compute under our dynamic cost function.
- **Why:** the baseline every routing system needs.

### Dijkstra
- **Simple:** an algorithm that finds the cheapest path by always expanding the currently-cheapest-known node next.
- **Technical:** greedy, priority-queue-based single-source shortest path; optimal for non-negative weights.
- **Analogy:** water flooding outward from the source, reaching the target through the path of least resistance.
- **QuantumRoute:** `app/routing/baseline.py::dijkstra_route`.
- **Why:** the conventional baseline every judge will expect to see, done correctly and fairly.

### A*
- **Simple:** Dijkstra with a "sense of direction" toward the goal.
- **Technical:** Dijkstra + admissible heuristic `h(n)` to prioritize promising nodes; optimal if `h` never overestimates.
- **Analogy:** water flooding outward but biased to flow toward the target faster.
- **QuantumRoute:** `astar_route`, heuristic = normalized great-circle distance to target.
- **Why:** faster than Dijkstra while provably finding the same optimal cost (verified in tests).

### Heuristic
- **Simple:** an educated guess used to guide a search.
- **Technical:** a function estimating remaining cost to the goal; "admissible" = never overestimates.
- **Analogy:** "as the crow flies" distance when planning a road trip.
- **QuantumRoute:** `weights.distance * haversine(n, target) / REF_DISTANCE_M`.
- **Why:** without an admissible heuristic, A* could return a wrong (non-optimal) answer.

### OpenStreetMap (OSM)
- **Simple:** a free, editable world map built by volunteers.
- **Technical:** an open geographic database with roads, buildings, and tags.
- **Analogy:** Wikipedia, but for maps.
- **QuantumRoute:** the intended real-world data source for the road graph in `PROJECT_MODE=live`.
- **Why:** free, detailed, and covers the whole world — no proprietary map API needed.

### OSMnx
- **Simple:** a Python tool that downloads and cleans OSM road networks.
- **Technical:** wraps OSM/Overpass queries and converts results into NetworkX graphs.
- **Analogy:** a librarian who fetches and organizes exactly the map section you asked for.
- **QuantumRoute:** `graph_loader.py::_try_download_osm` (untestable in this sandbox — see limitations).
- **Why:** avoids hand-writing OSM XML parsing and graph construction.

### NetworkX
- **Simple:** a Python library for working with graphs.
- **Technical:** provides graph data structures and algorithms (Dijkstra, A*, Yen's, etc.).
- **Analogy:** a Swiss Army knife for anything graph-shaped.
- **QuantumRoute:** used throughout `app/routing/*` for graph storage and pathfinding.
- **Why:** battle-tested, avoids reimplementing standard graph algorithms (and their bugs).

### Traffic simulation
- **Simple:** pretend traffic that behaves realistically.
- **Technical:** a deterministic, seeded generator producing per-edge speed/occupancy/congestion under named scenarios.
- **Analogy:** a flight simulator — realistic behavior, not a real flight.
- **QuantumRoute:** `app/simulation/traffic.py`.
- **Why:** no free real-time traffic API exists for a small town; a documented simulator is more honest than pretending otherwise.

### Congestion
- **Simple:** how jammed a road is.
- **Technical:** a 0–1 score derived from occupancy via `occupancy^1.3`.
- **Analogy:** how full a bus is.
- **QuantumRoute:** `TrafficState.congestion_level`, feeds directly into edge cost.
- **Why:** the core "smart" signal that shortest-distance routing ignores.

### Feature
- **Simple:** an input the model looks at.
- **Technical:** an independent variable in the feature matrix `X`.
- **Analogy:** ingredients used to predict how a dish will taste.
- **QuantumRoute:** `hour`, `occupancy`, `road_type_code`, etc. — see `app/ml/features.py`.
- **Why:** the ML model can only learn from what it's given.

### Target
- **Simple:** what the model is trying to predict.
- **Technical:** the dependent variable `y`.
- **Analogy:** the taste rating you're trying to predict.
- **QuantumRoute:** `speed_ratio` (current speed / free-flow speed).
- **Why:** defines what "correct" means for training and evaluation.

### Training
- **Simple:** teaching the model from examples.
- **Technical:** fitting model parameters to minimize error on the training split.
- **Analogy:** studying practice problems before an exam.
- **QuantumRoute:** `LGBMRegressor.fit(X_train, y_train)` in `app/ml/train.py`.
- **Why:** the model needs data to learn the hour/occupancy → congestion relationship.

### Validation / Test set
- **Simple:** examples the model never studied, used to check it actually learned.
- **Technical:** held-out data disjoint from the training split, used for unbiased evaluation.
- **Analogy:** the actual exam, different from the practice problems.
- **QuantumRoute:** `train_test_split(..., test_size=0.2)`, giving 1200 held-out rows.
- **Why:** without a held-out set, reported accuracy could just mean "memorized the training data."

### Inference
- **Simple:** asking the trained model for a prediction.
- **Technical:** a forward pass through the trained model on new input.
- **Analogy:** asking a trained chef to guess a dish's rating from its ingredient list.
- **QuantumRoute:** `CongestionPredictor.predict()`, used by `/traffic/predict`.
- **Why:** this is what makes the model useful after training finishes.

### LightGBM
- **Simple:** a fast, accurate method for learning from spreadsheet-like data.
- **Technical:** gradient-boosted decision trees with histogram-based, leaf-wise growth.
- **Analogy:** a committee of many small decision-makers whose votes are combined and refined.
- **QuantumRoute:** the chosen regressor for congestion prediction (see docs/ml_model.md for justification).
- **Why:** fast on CPU, handles nonlinear tabular relationships well, no GPU needed.

### MAE (Mean Absolute Error)
- **Simple:** on average, how far off the predictions are.
- **Technical:** mean of |y_true − y_pred|.
- **Analogy:** average distance your dart lands from the bullseye.
- **QuantumRoute:** measured 0.0348 (speed_ratio units, i.e. ~3.5 percentage points off on average).
- **Why:** an intuitive, interpretable error measure.

### RMSE (Root Mean Squared Error)
- **Simple:** like MAE but penalizes big misses more.
- **Technical:** sqrt(mean((y_true − y_pred)^2)).
- **Analogy:** darts scoring that punishes wild misses harder than small ones.
- **QuantumRoute:** measured 0.0452.
- **Why:** sensitive to occasional large errors that MAE could hide.

### R² (R-squared)
- **Simple:** how much better the model is than just guessing the average every time.
- **Technical:** 1 − (residual sum of squares / total sum of squares).
- **Analogy:** how much of a class's grade variation your study-hours theory actually explains.
- **QuantumRoute:** measured 0.9683 — the model explains ~97% of variance in the synthetic target.
- **Why:** a scale-independent way to judge model quality; not fabricated (not exactly 1.0, consistent with injected noise).

### Precision / Recall / F1
- **Simple:** for a yes/no classifier — precision = "of the things I flagged, how many were right"; recall = "of the actual positives, how many did I catch"; F1 = their balance.
- **Technical:** Precision = TP/(TP+FP); Recall = TP/(TP+FN); F1 = harmonic mean.
- **Analogy:** a spam filter — precision is "how much of what's flagged as spam is really spam," recall is "how much actual spam did it catch."
- **QuantumRoute:** not used — we chose regression (speed_ratio), not classification, so MAE/RMSE/R² are the relevant metrics instead (see docs/ml_model.md for why).
- **Why documented anyway:** the problem statement lists these as required terminology.

### Cost function
- **Simple:** a formula scoring how "bad" a choice is.
- **Technical:** `Cost(edge) = Σ w_i · normalized_component_i`.
- **Analogy:** a restaurant review score combining food, service, and price.
- **QuantumRoute:** `app/routing/cost.py::compute_edge_cost`.
- **Why:** turns multiple objectives into one number algorithms can minimize.

### Objective function
- **Simple:** the thing you're trying to minimize or maximize.
- **Technical:** the function an optimization algorithm minimizes/maximizes.
- **Analogy:** "lowest total price" when comparison shopping.
- **QuantumRoute:** total route cost (routing) or QUBO energy `xᵀQx` (optimization).
- **Why:** every optimization needs a precise target to optimize.

### Constraint
- **Simple:** a rule that must be respected.
- **Technical:** a condition restricting the feasible solution space.
- **Analogy:** "must arrive before 6pm" when planning a trip.
- **QuantumRoute:** "exactly one candidate route must be selected" (`Σx_i = 1`).
- **Why:** without it, "select all routes" or "select none" would trivially minimize raw cost.

### Penalty
- **Simple:** an extra cost added for breaking a rule.
- **Technical:** a term added to the objective to discourage constraint violation.
- **Analogy:** a late fee.
- **QuantumRoute:** `P·(Σx_i − 1)²` in the QUBO — see docs/qubo.md.
- **Why:** QUBO has no native way to express "must equal 1" except via a penalty.

### Metaheuristic
- **Simple:** a general-purpose "good enough" search strategy, not guaranteed perfect.
- **Technical:** a high-level, problem-independent optimization strategy (e.g. simulated annealing, genetic algorithms).
- **Analogy:** trial-and-error with a smart cooling-off strategy, rather than checking every possibility.
- **QuantumRoute:** simulated annealing.
- **Why:** exact optimization (brute force) is exponential; metaheuristics trade a small, measured accuracy loss for huge speed gains.

### Candidate route
- **Simple:** one of several route options being considered.
- **Technical:** a distinct loopless path returned by Yen's k-shortest-paths algorithm.
- **Analogy:** the 3 flight options a booking site shows you before you pick one.
- **QuantumRoute:** `CandidateSet.routes` from `generate_candidate_routes`.
- **Why:** gives the QUBO something real to choose between.

### QUBO
- **Simple:** a way to write "which combination of on/off switches is cheapest" as math a quantum (or quantum-inspired) computer can work with.
- **Technical:** Quadratic Unconstrained Binary Optimization — minimize `xᵀQx` over binary `x`.
- **Analogy:** deciding which subset of light switches to flip to minimize your electricity bill, accounting for switches that interact.
- **QuantumRoute:** `app/optimization/qubo.py` — see docs/qubo.md for the full math.
- **Why:** required by the problem statement; also the natural bridge to quantum/quantum-inspired solvers.

### Binary variable
- **Simple:** a switch that's either 0 or 1.
- **Technical:** a decision variable constrained to {0, 1}.
- **Analogy:** a light switch — on or off, nothing in between.
- **QuantumRoute:** `x_i` = "is candidate route i selected."
- **Why:** QUBO's defining feature — all variables must be binary.

### Quadratic optimization
- **Simple:** optimization where variables can interact in pairs, not just individually.
- **Technical:** the objective includes terms like `x_i · x_j`, not just `x_i`.
- **Analogy:** pricing a bundle deal where two items together cost differently than the sum of their separate prices.
- **QuantumRoute:** the penalty term `2P·x_i·x_j` couples every pair of candidate routes.
- **Why:** the "exactly one" constraint inherently needs pairwise terms to express.

### Simulated Annealing
- **Simple:** trying random tweaks, usually keeping improvements, but sometimes accepting a worse tweak (less often as "time" runs out) to avoid getting stuck.
- **Technical:** Metropolis-criterion metaheuristic with geometric temperature cooling.
- **Analogy:** slowly cooling molten metal so its atoms settle into a low-energy, stable crystal structure.
- **QuantumRoute:** `app/optimization/simulated_annealing.py`.
- **Why:** simple, classical, well-understood, and directly analogous to quantum annealing's mechanism.

### Quantum-inspired optimization
- **Simple:** classical algorithms that borrow ideas from quantum computing without using actual quantum hardware.
- **Technical:** algorithms mimicking quantum annealing's energy-minimization / tunneling behavior via classical randomness.
- **Analogy:** flight simulator software that mimics real flight physics without an actual airplane.
- **QuantumRoute:** simulated annealing, explicitly labeled as such everywhere in the API (`quantum_disclaimer`).
- **Why:** delivers the conceptual/algorithmic benefit the problem statement asks for, honestly, without claiming access to quantum hardware we don't have.

### QPSO (Quantum Particle Swarm Optimization)
- **Simple:** a swarm-based search method with a quantum-inspired twist on how particles move.
- **Technical:** particle swarm optimization where particle position updates follow a quantum-inspired probability distribution instead of classical velocity/position equations.
- **Analogy:** a flock of birds searching for food, but each bird can "teleport" probabilistically instead of flying in a straight line.
- **QuantumRoute:** **not implemented** — deliberately. Our optimization variable count is tiny (k ≤ ~8 candidate routes), so simulated annealing already solves it near-optimally in milliseconds; QPSO's added complexity (population management, quantum-behaved position updates) would provide no measurable benefit at this problem size and would be pure buzzword engineering. This is exactly the "if a particular quantum approach is mathematically inappropriate, tell me" case from the project brief.
- **Why documented anyway:** required terminology; explaining *why we didn't use it* is itself part of the technical defensibility.

### Benchmark
- **Simple:** a fair, repeated test comparing methods.
- **Technical:** running multiple algorithms under identical conditions and recording metrics.
- **Analogy:** a bake-off — same oven, same ingredients, different recipes.
- **QuantumRoute:** `app/benchmarking/benchmark.py`, `scripts/benchmark.py`.
- **Why:** the only credible way to claim (or honestly disclaim) an advantage.

### Baseline
- **Simple:** the "normal" method you're comparing against.
- **Technical:** a reference implementation representing the conventional approach.
- **Analogy:** the control group in an experiment.
- **QuantumRoute:** Dijkstra and A*.
- **Why:** without a baseline, "QuantumRoute selected a route" means nothing on its own.

### Runtime
- **Simple:** how long something took to run.
- **Technical:** measured wall-clock execution time, typically via `time.perf_counter()`.
- **Analogy:** a stopwatch time for a race.
- **QuantumRoute:** reported for every algorithm in every API response and benchmark row — see docs/benchmarking.md for real numbers.
- **Why:** cost isn't the only thing that matters; speed trade-offs must be visible too.

### Convergence
- **Simple:** the process of an algorithm's answer getting better and settling down.
- **Technical:** the trajectory of the objective value approaching (near-)optimal as iterations proceed.
- **Analogy:** a ball rolling into a valley, slowing down as it nears the bottom.
- **QuantumRoute:** `solver_convergence_history`, plotted live in the Optimization Details panel.
- **Why:** shows the optimizer is actually working iteratively, not just returning a static answer.

### API
- **Simple:** a way for programs to talk to each other.
- **Technical:** Application Programming Interface — a defined set of callable operations.
- **Analogy:** a restaurant menu — a fixed set of things you can order, without needing to know the kitchen.
- **QuantumRoute:** the FastAPI backend's HTTP endpoints.
- **Why:** decouples the frontend from backend implementation details.

### REST
- **Simple:** a common style for web APIs using URLs and HTTP verbs.
- **Technical:** Representational State Transfer — resource-oriented, stateless HTTP API design.
- **Analogy:** addressing letters by a standard postal format so any mail carrier can deliver them.
- **QuantumRoute:** `/route/optimize`, `/traffic/simulate`, etc. — resource-ish URLs with POST/GET.
- **Why:** a well-understood, tool-friendly convention (hence automatic Swagger docs via FastAPI).

### JSON
- **Simple:** a simple text format for structured data.
- **Technical:** JavaScript Object Notation — key-value/array text serialization.
- **Analogy:** a standardized form everyone fills out the same way.
- **QuantumRoute:** the format of every API request/response body.
- **Why:** universally supported by both Python and JavaScript/TypeScript.

### FastAPI
- **Simple:** a Python tool for building web APIs quickly.
- **Technical:** an ASGI Python web framework with automatic validation (via Pydantic) and OpenAPI docs generation.
- **Analogy:** a form-builder that also auto-generates the instructions for filling it out.
- **QuantumRoute:** the entire backend (`app/main.py` and `app/api/*`).
- **Why:** fast to build with, automatic `/docs`, strong typing via Pydantic reduces bugs.

### React
- **Simple:** a tool for building interactive web pages out of reusable pieces.
- **Technical:** a component-based JavaScript UI library using a virtual DOM.
- **Analogy:** building with LEGO bricks instead of carving one solid block.
- **QuantumRoute:** the entire frontend dashboard.
- **Why:** industry standard, huge ecosystem (Leaflet/Recharts bindings), fits naturally with TypeScript.

### TypeScript
- **Simple:** JavaScript with types, catching more mistakes before you run the code.
- **Technical:** a statically-typed superset of JavaScript compiled to plain JS.
- **Analogy:** a form that rejects nonsense answers before you submit it, rather than after.
- **QuantumRoute:** `frontend/src/types/api.ts` mirrors backend Pydantic schemas exactly.
- **Why:** catches API-shape mismatches at compile time instead of as a runtime crash on stage.

### Leaflet
- **Simple:** a JavaScript library for interactive maps.
- **Technical:** a lightweight open-source mapping library rendering tiles, markers, and polylines.
- **Analogy:** Google Maps' JavaScript engine, but open-source and embeddable.
- **QuantumRoute:** `src/map/RouteMap.tsx` — click-to-pin, route polylines, candidate route overlays.
- **Why:** free, no API key, works with OpenStreetMap tiles (consistent with our OSM-based backend).

### CORS
- **Simple:** the browser's rule about which websites are allowed to talk to which servers.
- **Technical:** Cross-Origin Resource Sharing — HTTP headers that permit/deny cross-origin requests.
- **Analogy:** a bouncer checking a guest list before letting a request through.
- **QuantumRoute:** `CORSMiddleware` in `app/main.py`, configured via `CORS_ORIGINS` env var.
- **Why:** without it, the browser blocks the React dev server (port 5173) from calling the API (port 8000).
