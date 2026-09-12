import { useCallback, useEffect, useState } from "react";
import RouteMap from "../map/RouteMap";
import WeightSliders from "../components/WeightSliders";
import ComparisonTable from "../components/ComparisonTable";
import OptimizationDetails from "../components/OptimizationDetails";
import { formatDistance, formatDuration } from "../utils/format";
import {
  getBaselineRoute,
  getSystemStatus,
  optimizeRoute,
} from "../services/api";
import type {
  BaselineResponse,
  OptimizationWeights,
  OptimizeRouteResponse,
  SystemStatus,
} from "../types/api";

const DEFAULT_WEIGHTS: OptimizationWeights = {
  travel_time: 35,
  congestion: 30,
  distance: 15,
  fuel: 10,
  intersection: 5,
  incident: 5,
};

// Research graph is the METR-LA / Los Angeles OSM footprint.
const RESEARCH_CENTER: [number, number] = [34.135, -118.278];

const DEFAULT_RESEARCH_TIMESTAMP = "2012-03-01T08:00";

type PinMode = "source" | "destination" | null;

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [source, setSource] = useState<[number, number] | null>(null);
  const [destination, setDestination] = useState<[number, number] | null>(null);
  const [pinMode, setPinMode] = useState<PinMode>("source");

  const [scenario, setScenario] = useState("low");
  const [timestamp, setTimestamp] = useState(DEFAULT_RESEARCH_TIMESTAMP);
  const [weights, setWeights] =
    useState<OptimizationWeights>(DEFAULT_WEIGHTS);

  const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
  const [optimized, setOptimized] =
    useState<OptimizeRouteResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const isResearch = status?.project_mode === "research";

  useEffect(() => {
    getSystemStatus()
      .then(setStatus)
      .catch((e) => setStatusError(String(e)));
  }, []);

  const handleMapClick = useCallback(
    (lat: number, lon: number) => {
      if (pinMode === "source") {
        setSource([lat, lon]);
        setPinMode("destination");
      } else if (pinMode === "destination") {
        setDestination([lat, lon]);
        setPinMode(null);
      }
    },
    [pinMode],
  );

  const runOptimization = useCallback(async () => {
    if (!source || !destination) {
      setRunError("Select a source and destination on the map first.");
      return;
    }

    if (isResearch && !timestamp) {
      setRunError("Select a historical METR-LA timestamp.");
      return;
    }

    setLoading(true);
    setRunError(null);

    try {
      const src = { lat: source[0], lon: source[1] };
      const dst = { lat: destination[0], lon: destination[1] };

      const researchTimestamp = isResearch ? timestamp : undefined;

      const [baselineRes, optimizedRes] = await Promise.all([
        getBaselineRoute(
          src,
          dst,
          scenario,
          weights,
          researchTimestamp,
        ),
        optimizeRoute(
          src,
          dst,
          scenario,
          weights,
          researchTimestamp,
        ),
      ]);

      setBaseline(baselineRes);
      setOptimized(optimizedRes);
    } catch (e) {
      setRunError(String(e));
    } finally {
      setLoading(false);
    }
  }, [source, destination, scenario, timestamp, weights, isResearch]);

  const selectedRoute = optimized?.selected_route ?? null;

  return (
    <div className="h-screen w-screen flex flex-col bg-[var(--qr-bg)] text-[var(--qr-text)]">
      <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--qr-border)] bg-[var(--qr-panel)]">
<div className="flex items-baseline gap-3">
          <h1 className="text-lg font-semibold tracking-tight">
            QuantumRoute
          </h1>

          <span className="text-xs text-[var(--qr-text-muted)]">
            Intelligent traffic route optimization — SIH260137
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono-qr text-[var(--qr-text-muted)]">
          {statusError && (
            <span className="text-[var(--qr-red)]">
              backend unreachable
            </span>
          )}

          {status && (
            <>
              <span>
                mode:{" "}
                <span className="text-[var(--qr-text)]">
                  {status.project_mode}
                </span>
              </span>

              <span>
                graph:{" "}
                <span className="text-[var(--qr-text)]">
                  {status.graph_source}
                </span>
              </span>

              <span>
                nodes/edges:{" "}
                <span className="text-[var(--qr-text)]">
                  {status.num_nodes}/{status.num_edges}
                </span>
              </span>

              <span
                className={
                  status.ml_model_loaded
                    ? "text-[var(--qr-cyan)]"
                    : "text-[var(--qr-amber)]"
                }
              >
                ML{" "}
                {status.ml_model_loaded
                  ? "ready"
                  : "not loaded"}
              </span>
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <aside className="w-80 flex-shrink-0 border-r border-[var(--qr-border)] bg-[var(--qr-panel)] overflow-y-auto p-4 flex flex-col gap-5">
          
          {isResearch && (
            <section className="rounded-lg border border-[var(--qr-cyan)]/40 bg-[var(--qr-cyan)]/5 p-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs uppercase tracking-wide text-[var(--qr-cyan)]">
                  Research Mode
                </h2>

                <span className="text-[10px] font-mono-qr text-[var(--qr-cyan)]">
                  LIVE CONFIG
                </span>
              </div>

              <div className="mt-3 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Traffic dataset
                  </span>
                  <span className="font-mono-qr">
                    METR-LA
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Provenance
                  </span>
                  <span className="font-mono-qr text-[var(--qr-cyan)]">
                    REAL_HISTORICAL
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Road network
                  </span>
                  <span className="font-mono-qr">
                    OpenStreetMap
                  </span>
                </div>
              </div>
            </section>
          )}

          <section>
            <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
              Source &amp; destination
            </h2>

            <div className="flex flex-col gap-2 text-sm">
              <button
                onClick={() => setPinMode("source")}
                className={`text-left px-3 py-2 rounded border ${
                  pinMode === "source"
                    ? "border-[var(--qr-cyan)] bg-[var(--qr-cyan)]/10"
                    : "border-[var(--qr-border)] bg-[var(--qr-panel-raised)]"
                }`}
              >
                <div className="text-[10px] uppercase text-[var(--qr-text-muted)]">
                  Source
                </div>

                <div className="font-mono-qr">
                  {source
                    ? `${source[0].toFixed(5)}, ${source[1].toFixed(5)}`
                    : "Click map to set"}
                </div>
              </button>

              <button
                onClick={() => setPinMode("destination")}
                className={`text-left px-3 py-2 rounded border ${
                  pinMode === "destination"
                    ? "border-[var(--qr-red)] bg-[var(--qr-red)]/10"
                    : "border-[var(--qr-border)] bg-[var(--qr-panel-raised)]"
                }`}
              >
                <div className="text-[10px] uppercase text-[var(--qr-text-muted)]">
                  Destination
                </div>

                <div className="font-mono-qr">
                  {destination
                    ? `${destination[0].toFixed(5)}, ${destination[1].toFixed(5)}`
                    : "Click map to set"}
                </div>
              </button>
            </div>
          </section>

          {isResearch ? (
            <section>
              <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
                Historical traffic
              </h2>

              <div className="rounded-lg border border-[var(--qr-border)] bg-[var(--qr-panel-raised)] p-3">
                <label className="text-xs text-[var(--qr-text-muted)]">
                  METR-LA timestamp

                  <input
                    type="datetime-local"
                    step={300}
                    value={timestamp}
                    min="2012-03-01T00:00"
                    max="2012-06-27T23:55"
                    onChange={(e) => setTimestamp(e.target.value)}
                    className="w-full mt-2 bg-[var(--qr-bg)] border border-[var(--qr-border)] rounded px-2 py-2 text-sm text-[var(--qr-text)] font-mono-qr"
                  />
                </label>

                <div className="mt-2 text-[10px] text-[var(--qr-text-muted)] leading-relaxed">
                  Historical observations are evaluated at
                  five-minute METR-LA timestamps.
                </div>
              </div>
            </section>
          ) : (
            <section>
              <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
                Traffic scenario
              </h2>

              <div className="grid grid-cols-2 gap-2">
                {[
                  ["low", "Low", "Free-flowing"],
                  ["medium", "Medium", "Typical midday"],
                  ["heavy", "Heavy", "Congested"],
                  ["peak", "Peak hour", "Rush hour"],
                  ["incident", "Incident", "Simulated accident"],
                  ["closure", "Road closure", "Segments blocked"],
                ].map(([value, label, hint]) => (
                  <button
                    key={value}
                    onClick={() => setScenario(value)}
                    className={`text-left px-2.5 py-2 rounded border text-xs ${
                      scenario === value
                        ? "border-[var(--qr-cyan)] bg-[var(--qr-cyan)]/10 text-[var(--qr-text)]"
                        : "border-[var(--qr-border)] bg-[var(--qr-panel-raised)] text-[var(--qr-text-muted)]"
                    }`}
                  >
                    <div className="font-medium">{label}</div>
                    <div className="text-[10px] opacity-70">
                      {hint}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
              Optimization weights
            </h2>

            <WeightSliders
              weights={weights}
              onChange={setWeights}
            />
          </section>

          <button
            onClick={runOptimization}
            disabled={loading}
            className="mt-auto w-full py-2.5 rounded bg-[var(--qr-cyan)] text-[#04211d] font-medium text-sm disabled:opacity-50"
          >
            {loading ? "Optimizing…" : "Run route analysis"}
          </button>

            <a
              href={
                source && destination
                  ? (() => {
                      const p = new URLSearchParams({
                        source: `${source[0]},${source[1]}`,
                        destination: `${destination[0]},${destination[1]}`,
                        scenario,
                        timestamp,
                        travelTime: String(weights.travel_time),
                        congestion: String(weights.congestion),
                        distance: String(weights.distance),
                        fuel: String(weights.fuel),
                        intersection: String(weights.intersection),
                        incident: String(weights.incident),
                      });
                      return `/analysis?${p.toString()}`;
                    })()
                  : "#"
              }
              className="analysis-button"
              onClick={(e) => {
                if (!source || !destination) e.preventDefault();
              }}
            >
              ANALYSIS →
            </a>

          {runError && (
            <p className="text-xs text-[var(--qr-red)]">
              {runError}
            </p>
          )}
        </aside>

        <main className="flex-1 min-w-0 relative">
          <RouteMap
            center={isResearch ? RESEARCH_CENTER : RESEARCH_CENTER}
            source={source}
            destination={destination}
            selectedRoute={selectedRoute}
            candidateRoutes={optimized?.candidate_routes ?? []}
            onMapClick={handleMapClick}
          />

          {pinMode && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-[var(--qr-panel)]/95 border border-[var(--qr-border)] rounded-full px-4 py-1.5 text-xs">
              Click the map to place the {pinMode}
            </div>
          )}

          {isResearch && (
            <div className="absolute top-3 left-3 bg-[var(--qr-panel)]/95 border border-[var(--qr-border)] rounded-lg px-3 py-2 text-xs">
              <div className="font-medium text-[var(--qr-cyan)]">
                METR-LA • Historical traffic
              </div>
              <div className="text-[10px] text-[var(--qr-text-muted)] font-mono-qr mt-1">
                {timestamp.replace("T", " ")}
              </div>
            </div>
          )}

          {selectedRoute && (
            <div className="absolute bottom-4 left-4 bg-[var(--qr-panel)]/95 border border-[var(--qr-border)] rounded-lg px-4 py-3 flex gap-6">
              <div>
                <div className="text-[10px] uppercase text-[var(--qr-text-muted)]">
                  ETA
                </div>
                <div className="font-mono-qr text-lg">
                  {formatDuration(
                    selectedRoute.total_travel_time_sec,
                  )}
                </div>
              </div>

              <div>
                <div className="text-[10px] uppercase text-[var(--qr-text-muted)]">
                  Distance
                </div>
                <div className="font-mono-qr text-lg">
                  {formatDistance(
                    selectedRoute.total_distance_m,
                  )}
                </div>
              </div>

              <div>
                <div className="text-[10px] uppercase text-[var(--qr-text-muted)]">
                  Optimization score
                </div>
                <div className="font-mono-qr text-lg text-[var(--qr-cyan)]">
                  {selectedRoute.total_cost.toFixed(4)}
                </div>
              </div>
            </div>
          )}
        </main>

        <aside className="w-96 flex-shrink-0 border-l border-[var(--qr-border)] bg-[var(--qr-panel)] overflow-y-auto p-4 flex flex-col gap-6">
          <section>
            <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
              Algorithm comparison
            </h2>

            <ComparisonTable
              dijkstra={baseline?.dijkstra ?? null}
              astar={baseline?.astar ?? null}
              quantumRoute={optimized?.selected_route ?? null}
              quantumRuntimeMs={
                optimized?.total_pipeline_time_ms ?? null
              }
            />
          </section>

          {isResearch && (
            <section>
              <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
                Data provenance
              </h2>

              <div className="rounded-lg border border-[var(--qr-border)] bg-[var(--qr-panel-raised)] p-3 space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Traffic
                  </span>
                  <span className="font-mono-qr text-[var(--qr-cyan)]">
                    REAL_HISTORICAL
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Dataset
                  </span>
                  <span className="font-mono-qr">
                    METR-LA
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Road network
                  </span>
                  <span className="font-mono-qr">
                    REAL_GEOGRAPHIC
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-[var(--qr-text-muted)]">
                    Synthetic traffic
                  </span>
                  <span className="font-mono-qr">
                    NOT USED
                  </span>
                </div>

                {baseline?.timestamp && (
                  <div className="flex justify-between">
                    <span className="text-[var(--qr-text-muted)]">
                      Timestamp
                    </span>
                    <span className="font-mono-qr">
                      {baseline.timestamp.replace("T", " ")}
                    </span>
                  </div>
                )}
              </div>
            </section>
          )}

          {!isResearch && (
            <section>
              <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
                AI congestion prediction
              </h2>

              <p className="text-xs text-[var(--qr-text-muted)] leading-relaxed">
                Demo-mode prediction panel is available only when
                synthetic/demo traffic is enabled.
              </p>
            </section>
          )}

          <section>
            <h2 className="text-xs uppercase tracking-wide text-[var(--qr-text-muted)] mb-2">
              Optimization details
            </h2>

            <OptimizationDetails result={optimized} />
          </section>
        </aside>
      </div>
    </div>
  );
}
