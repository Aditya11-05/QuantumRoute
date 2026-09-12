import { useEffect, useMemo, useState } from "react";



import { getRouteAnalysis } from "../services/analysisApi";

import TrafficHeatmap from "../components/TrafficHeatmap";

import { getTrafficMap } from "../services/trafficMapApi";



import type {

  AnalysisRequest,

  AnalysisRoute,

  RouteAnalysisResponse,

} from "../types/api";



import type { TrafficMapResponse } from "../types/trafficMap";



import "./Analysis.css";





function formatDistance(m: number) {

  return m >= 1000

    ? `${(m / 1000).toFixed(2)} km`

    : `${m.toFixed(0)} m`;

}





function formatDuration(seconds: number) {

  const minutes = seconds / 60;



  if (minutes >= 60) {

    const h = Math.floor(minutes / 60);

    const min = Math.round(minutes % 60);

    return `${h}h ${min}m`;

  }



  return `${minutes.toFixed(1)} min`;

}





function formatCost(value: number) {

  return value.toFixed(4);

}





function formatPct(value: number | null | undefined) {

  return value == null

    ? "—"

    : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;

}





function safeNumber(value: string | null, fallback: number) {

  const parsed = Number(value);

  return Number.isFinite(parsed) ? parsed : fallback;

}





function PerformanceCard({

  title,

  route,

  tag,

}: {

  title: string;

  route: AnalysisRoute | null;

  tag?: string;

}) {

  if (!route) return null;



  return (

    <article className="analysis-card performance-card">

      <div className="analysis-card-title">

        <span>{title}</span>

        {tag && <span className="analysis-tag">{tag}</span>}

      </div>



      <div className="analysis-big-number">

        {formatDistance(route.total_distance_m)}

      </div>



      <div className="analysis-muted">

        route distance

      </div>



      <div className="analysis-metric-row">

        <span>ETA</span>

        <strong>

          {formatDuration(route.total_travel_time_sec)}

        </strong>

      </div>



      <div className="analysis-metric-row">

        <span>Objective cost</span>

        <strong>

          {formatCost(route.total_cost)}

        </strong>

      </div>



      <div className="analysis-metric-row">

        <span>Runtime</span>

        <strong>

          {route.computation_time_ms.toFixed(2)} ms

        </strong>

      </div>



      <div className="analysis-metric-row">

        <span>Edges</span>

        <strong>

          {route.num_edges.toLocaleString()}

        </strong>

      </div>

    </article>

  );

}





function InfoCard({

  label,

  value,

  accent = false,

}: {

  label: string;

  value: string;

  accent?: boolean;

}) {

  return (

    <div className="analysis-info-card">

      <span>{label}</span>

      <strong className={accent ? "analysis-accent" : ""}>

        {value}

      </strong>

    </div>

  );

}





export default function Analysis() {

  const params = useMemo(

    () => new URLSearchParams(window.location.search),

    [],

  );



  const [data, setData] =

    useState<RouteAnalysisResponse | null>(null);



  const [loading, setLoading] =

    useState(true);



  const [error, setError] =

    useState<string | null>(null);



  /*

   * Traffic heatmap state

   *

   * This is deliberately separate from the route-analysis request.

   * The route analysis gives us the experiment results.

   * The traffic-map endpoint gives us only the real historical

   * sensor-to-OSM edges available for the same request/timestamp.

   */

  const [trafficMap, setTrafficMap] =

    useState<TrafficMapResponse | null>(null);



  const [trafficMapLoading, setTrafficMapLoading] =

    useState(false);



  const [trafficMapError, setTrafficMapError] =

    useState<string | null>(null);





  const request = useMemo<AnalysisRequest | null>(() => {

    const sourceLat = safeNumber(

      params.get("sourceLat"),

      NaN,

    );



    const sourceLon = safeNumber(

      params.get("sourceLon"),

      NaN,

    );



    const destLat = safeNumber(

      params.get("destLat"),

      NaN,

    );



    const destLon = safeNumber(

      params.get("destLon"),

      NaN,

    );





    if (

      ![

        sourceLat,

        sourceLon,

        destLat,

        destLon,

      ].every(Number.isFinite)

    ) {

      return null;

    }





    const timestamp =

      params.get("timestamp") || undefined;





    return {

      source: {

        lat: sourceLat,

        lon: sourceLon,

      },



      destination: {

        lat: destLat,

        lon: destLon,

      },



      traffic_scenario:

        params.get("scenario") ?? "low",



      timestamp,



      weights: {

        travel_time: safeNumber(

          params.get("travelTime"),

          0.35,

        ),



        congestion: safeNumber(

          params.get("congestion"),

          0.30,

        ),



        distance: safeNumber(

          params.get("distance"),

          0.15,

        ),



        fuel: safeNumber(

          params.get("fuel"),

          0.10,

        ),



        intersection: safeNumber(

          params.get("intersection"),

          0.05,

        ),



        incident: safeNumber(

          params.get("incident"),

          0.05,

        ),

      },

    };

  }, [params]);





  /*

   * Load the main route-analysis experiment.

   */

  useEffect(() => {

    if (!request) {

      setError(

        "This page needs a route selected from the Dashboard.",

      );



      setLoading(false);



      return;

    }





    let cancelled = false;





    (async () => {

      try {

        setLoading(true);

        setError(null);



        const result =

          await getRouteAnalysis(request);



        if (!cancelled) {

          setData(result);

        }

      } catch (e) {

        if (!cancelled) {

          setError(

            e instanceof Error

              ? e.message

              : "Failed to load route analysis.",

          );

        }

      } finally {

        if (!cancelled) {

          setLoading(false);

        }

      }

    })();





    return () => {

      cancelled = true;

    };

  }, [request]);





  /*

   * Load the historical traffic heatmap using the EXACT SAME

   * route request and timestamp.

   *

   * This endpoint intentionally returns only edges for which

   * METR-LA observations can actually be mapped.

   *

   * We therefore do NOT fabricate congestion values for

   * unsensed road segments.

   */

  useEffect(() => {

    if (!request) {

      setTrafficMap(null);

      return;

    }





    let cancelled = false;



    setTrafficMapLoading(true);

    setTrafficMapError(null);





    getTrafficMap(request)

      .then((result) => {

        if (!cancelled) {

          setTrafficMap(result);

        }

      })

      .catch((e) => {

        if (!cancelled) {

          setTrafficMapError(

            e instanceof Error

              ? e.message

              : String(e),

          );

        }

      })

      .finally(() => {

        if (!cancelled) {

          setTrafficMapLoading(false);

        }

      });





    return () => {

      cancelled = true;

    };

  }, [request]);





  if (loading) {

    return (

      <main className="analysis-page">

        <div className="analysis-state">

          <div className="analysis-spinner" />



          <h1>

            Running route experiment

          </h1>



          <p>

            Evaluating the same historical traffic

            snapshot, road network, weights and candidate

            set used by QuantumRoute.

          </p>

        </div>

      </main>

    );

  }





  if (error || !data) {

    return (

      <main className="analysis-page">

        <div className="analysis-state">

          <h1>

            Analysis unavailable

          </h1>



          <p>

            {error ??

              "No analysis result was returned."}

          </p>



          <button

            className="analysis-button"

            onClick={() => {

              window.location.href = "/";

            }}

          >

            ← Back to Dashboard

          </button>

        </div>

      </main>

    );

  }





  const dijkstra =

    data.baseline.dijkstra;



  const astar =

    data.baseline.astar;



  const selected =

    data.optimization.selected_route;



  const candidates =

    data.optimization.candidate_routes ?? [];



  const selectedIndex =

    data.optimization.selected_index;



  const exactIndex =

    data.optimization.exact_optimal_index;





  const runtimeValues = [

    {

      label: "Dijkstra",

      value: dijkstra?.computation_time_ms ?? 0,

    },



    {

      label: "A*",

      value: astar?.computation_time_ms ?? 0,

    },



    {

      label: "QuantumRoute",

      value:

        data.optimization.total_pipeline_time_ms,

    },

  ];





  const maxRuntime =

    Math.max(

      ...runtimeValues.map(

        (x) => x.value,

      ),

      1,

    );





  return (

    <main className="analysis-page">



      {/* =====================================================

          HEADER

          ===================================================== */}



      <header className="analysis-header">

        <div>

          <div className="analysis-eyebrow">

            QUANTUMROUTE / RESEARCH ANALYSIS

          </div>



          <h1>

            Route Experiment

          </h1>



          <p>

            Same route request, same historical traffic

            snapshot, and the same objective weights are

            evaluated across baseline and optimization methods.

          </p>

        </div>





        <button

          className="analysis-button analysis-back"

          onClick={() => {

            window.location.href = "/";

          }}

        >

          ← Dashboard

        </button>

      </header>





      {/* =====================================================

          STATUS

          ===================================================== */}



      <section className="analysis-grid status-grid">



        <InfoCard

          label="Traffic"

          value={

            data.traffic.traffic_provenance

          }

          accent

        />





        <InfoCard

          label="Network"

          value={`${data.network.num_nodes.toLocaleString()} nodes`}

        />





        <InfoCard

          label="Optimizer"

          value={

            "Simulated Annealing"

          }

        />





        <InfoCard

          label="Candidate verification"

          value={

            data.optimization

              .matches_exact_optimum

              ? "EXACT CANDIDATE OPTIMUM"

              : "NOT EXACT"

          }

          accent={Boolean(
            data.optimization.matches_exact_optimum,
          )}

        />



      </section>





      {/* =====================================================

          01 — ROUTE PERFORMANCE

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>01</span>

            <h2>

              Route performance

            </h2>

          </div>



          <p>

            All three views use the same request and

            traffic snapshot.

          </p>



        </div>





        <div className="performance-grid">



          <PerformanceCard

            title="Dijkstra"

            route={dijkstra}

            tag="BASELINE"

          />





          <PerformanceCard

            title="A*"

            route={astar}

          />





          <PerformanceCard

            title="QuantumRoute"

            route={selected}

            tag={

              selectedIndex != null

                ? `CANDIDATE ${selectedIndex + 1}`

                : "SELECTED"

            }

          />



        </div>



      </section>





      {/* =====================================================

          02A — HISTORICAL TRAFFIC HEATMAP

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>02A</span>

            <h2>

              Traffic heatmap

            </h2>

          </div>



          <p>

            Real historical METR-LA observations mapped

            onto verified OSM edges. Unsensed road segments

            are intentionally not assigned fabricated traffic.

          </p>



        </div>





        <TrafficHeatmap

          data={trafficMap}

          loading={trafficMapLoading}

          error={trafficMapError}

          source={request!.source}

          destination={request!.destination}


      />



      </section>





      {/* =====================================================

          02 — MEASURED COMPARISON

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>02</span>

            <h2>

              Measured comparison

            </h2>

          </div>



          <p>

            Δ values are measured from the returned

            experiment; no improvement is fabricated.

          </p>



        </div>





        <div className="comparison-grid">



          <InfoCard

            label="Distance change vs Dijkstra"

            value={

              formatPct(

                data.comparison

                  .distance_change_pct,

              )

            }

          />





          <InfoCard

            label="Travel-time change vs Dijkstra"

            value={

              formatPct(

                data.comparison

                  .travel_time_change_pct,

              )

            }

          />





          <InfoCard

            label="Objective-cost change vs Dijkstra"

            value={

              formatPct(

                data.comparison

                  .cost_change_pct,

              )

            }

          />



        </div>





        <div className="analysis-callout">



          <div className="callout-label">

            INTERPRETATION

          </div>



          <div>

            <p>

              {data.interpretation.optimizer}

            </p>



            <p>

              {data.interpretation.route_comparison}

            </p>

          </div>



        </div>



      </section>





      {/* =====================================================

          03 — CANDIDATE ROUTES

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>03</span>

            <h2>

              Candidate route landscape

            </h2>

          </div>



          <p>

            Exact verification is against the generated

            candidate set, not the entire road network.

          </p>



        </div>





        <div className="candidate-table-wrap">



          <table className="candidate-table">



            <thead>

              <tr>

                <th>Route</th>

                <th>Distance</th>

                <th>ETA</th>

                <th>Cost</th>

                <th>Status</th>

              </tr>

            </thead>





            <tbody>



              {candidates.map(

                (candidate, index) => {



                  const selectedRow =

                    index === selectedIndex;



                  const exactRow =

                    index === exactIndex;





                  return (

                    <tr

                      className={

                        selectedRow

                          ? "selected-row"

                          : ""

                      }

                      key={`${index}-${candidate.total_cost}`}

                    >



                      <td>

                        <strong>

                          Candidate {index + 1}

                        </strong>

                      </td>





                      <td>

                        {formatDistance(

                          candidate.total_distance_m,

                        )}

                      </td>





                      <td>

                        {formatDuration(

                          candidate.total_travel_time_sec,

                        )}

                      </td>





                      <td>

                        {formatCost(

                          candidate.total_cost,

                        )}

                      </td>





                      <td>



                        {selectedRow && (

                          <span className="analysis-badge selected">

                            SELECTED

                          </span>

                        )}





                        {exactRow && (

                          <span className="analysis-badge exact">

                            EXACT MIN

                          </span>

                        )}



                      </td>



                    </tr>

                  );

                },

              )}



            </tbody>



          </table>



        </div>



      </section>





      {/* =====================================================

          04 — OPTIMIZATION INTERNALS

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>04</span>

            <h2>

              Optimization internals

            </h2>

          </div>



        </div>





        <div className="analysis-grid four-col">



          <InfoCard

            label="QUBO variables"

            value={String(

              data.optimization.qubo_size,

            )}

          />





          <InfoCard

            label="Penalty coefficient"

            value={data.optimization.qubo_penalty.toFixed(4)}

          />





          <InfoCard

            label="SA iterations"

            value={data.optimization.solver_iterations.toLocaleString()}

          />





          <InfoCard

            label="Solver runtime"

            value={`${data.optimization.solver_runtime_ms.toFixed(2)} ms`}

          />





          <InfoCard

            label="Best energy"

            value={data.optimization.solver_best_energy.toFixed(4)}

          />





          <InfoCard

            label="Feasible selection"

            value={

              data.optimization.feasible_selection

                ? "YES"

                : "NO"

            }

            accent={

              data.optimization.feasible_selection

            }

          />





          <InfoCard

            label="Repair applied"

            value={

              data.optimization.was_repaired

                ? "YES"

                : "NO"

            }

          />





          <InfoCard

            label="Optimality gap"

            value={`${

              data.optimization

                .optimality_gap_pct?.toFixed(2) ??

              "—"

            }%`}

            accent={

              data.optimization

                .optimality_gap_pct === 0

            }

          />



        </div>





        <div className="analysis-runtime-card">



          <div className="callout-label">

            COMPUTATION TIME

          </div>





          {runtimeValues.map(

            (item) => (



              <div

                className="runtime-row"

                key={item.label}

              >



                <span>

                  {item.label}

                </span>





                <div className="runtime-track">



                  <div

                    className="runtime-fill"

                    style={{

                      width: `${Math.max(

                        2,

                        (item.value /

                          maxRuntime) *

                          100,

                      )}%`,

                    }}

                  />



                </div>





                <strong>

                  {item.value.toFixed(2)} ms

                </strong>



              </div>



            ),

          )}



        </div>



      </section>





      {/* =====================================================

          05 — RESEARCH PROVENANCE

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>05</span>

            <h2>

              Research provenance

            </h2>

          </div>



        </div>





        <div className="analysis-grid four-col">



          <InfoCard

            label="Dataset"

            value="METR-LA"

          />





          <InfoCard

            label="Traffic provenance"

            value={

              data.traffic

                .traffic_provenance

            }

            accent

          />





          <InfoCard

            label="Road network"

            value={

              data.network.graph_source

            }

          />





          <InfoCard

            label="Region"

            value={

              data.network.region

            }

          />





          <InfoCard

            label="Synthetic traffic"

            value="NOT USED"

          />





          <InfoCard

            label="Timestamp"

            value={

              data.traffic.timestamp
                ? data.traffic.timestamp.replace("T", " ")
                : "Not available"

            }

          />





          <InfoCard

            label="Source snap"

            value={`${data.snap.source_distance_m.toFixed(1)} m`}

          />





          <InfoCard

            label="Destination snap"

            value={`${data.snap.destination_distance_m.toFixed(1)} m`}

          />



        </div>



      </section>





      {/* =====================================================

          06 — OBJECTIVE WEIGHTS

          ===================================================== */}



      <section className="analysis-section">



        <div className="analysis-section-heading">



          <div>

            <span>06</span>

            <h2>

              Objective weights

            </h2>

          </div>



        </div>





        <div className="weight-bars">



          {Object.entries(

            data.weights,

          ).map(([key, value]) => (



            <div

              className="weight-row"

              key={key}

            >



              <span>

                {key.replaceAll(

                  "_",

                  " ",

                )}

              </span>





              <div className="weight-track">



                <div

                  className="weight-fill"

                  style={{

                    width: `${value * 100}%`,

                  }}

                />



              </div>





              <strong>

                {(value * 100).toFixed(0)}%

              </strong>



            </div>



          ))}



        </div>



      </section>





      {/* =====================================================

          DISCLAIMER

          ===================================================== */}



      <section className="analysis-disclaimer">



        <strong>

          Quantum computing disclaimer

        </strong>



        <p>

          {data.quantum_disclaimer}

        </p>



      </section>



    </main>

  );

}
