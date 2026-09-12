import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Coordinate } from "../types/api";
import type { TrafficMapResponse } from "../types/trafficMap";

interface Props {
  data: TrafficMapResponse | null;
  loading: boolean;
  error: string | null;
  source: Coordinate;
  destination: Coordinate;
}

function congestionColor(value: number): string {
  const x = Math.max(0, Math.min(1, value));
  if (x < 0.2) return "#22c55e";
  if (x < 0.4) return "#84cc16";
  if (x < 0.6) return "#facc15";
  if (x < 0.8) return "#f97316";
  return "#ef4444";
}

export default function TrafficHeatmap({
  data,
  loading,
  error,
  source,
  destination,
}: Props) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, { zoomControl: true }).setView(
      [source.lat, source.lon],
      13,
    );

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, [source.lat, source.lon]);

  const hotspotCount = useMemo(
    () => data?.segments.filter((segment) => segment.congestion >= 0.6).length ?? 0,
    [data],
  );

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();

    if (data?.segments.length) {
      const bounds: [number, number][] = [];

      data.segments.forEach((segment) => {
        const latlngs = segment.coordinates.map(([lat, lon]) => [lat, lon] as [number, number]);
        latlngs.forEach((point) => bounds.push(point));

        L.polyline(latlngs, {
          color: congestionColor(segment.congestion),
          weight: 5,
          opacity: 0.9,
          lineCap: "round",
        })
          .bindTooltip(
            `${segment.highway} · ${segment.speed_kmh.toFixed(1)} km/h · ${(segment.congestion * 100).toFixed(0)}% congestion`,
          )
          .addTo(layer);
      });

      if (bounds.length) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
    }

    L.circleMarker([source.lat, source.lon], {
      radius: 7,
      color: "#00e5cc",
      fillColor: "#00e5cc",
      fillOpacity: 1,
      weight: 2,
    }).bindTooltip("Source").addTo(layer);

    L.circleMarker([destination.lat, destination.lon], {
      radius: 7,
      color: "#ef4444",
      fillColor: "#ef4444",
      fillOpacity: 1,
      weight: 2,
    }).bindTooltip("Destination").addTo(layer);
  }, [data, source.lat, source.lon, destination.lat, destination.lon]);

  return (
    <div className="analysis-heatmap-shell">
      <div className="analysis-heatmap-map" ref={containerRef} />

      <div className="analysis-heatmap-overlay">
        <div className="analysis-heatmap-title">Historical congestion field</div>
        <div className="analysis-heatmap-subtitle">
          METR-LA observed sensor-to-OSM edge traffic · no synthetic interpolation
        </div>
        <div className="analysis-heatmap-legend">
          <span>0%</span>
          <i style={{ background: "#22c55e" }} />
          <i style={{ background: "#84cc16" }} />
          <i style={{ background: "#facc15" }} />
          <i style={{ background: "#f97316" }} />
          <i style={{ background: "#ef4444" }} />
          <span>100%</span>
        </div>
      </div>

      {loading && <div className="analysis-heatmap-state">Loading historical traffic…</div>}
      {error && !loading && <div className="analysis-heatmap-state analysis-heatmap-error">{error}</div>}
      {!loading && !error && data && (
        <div className="analysis-heatmap-stats">
          <span><strong>{data.observed_edges.toLocaleString()}</strong> observed edges</span>
          <span><strong>{data.coverage_pct.toFixed(2)}%</strong> network coverage</span>
          <span><strong>{hotspotCount}</strong> hotspots ≥60%</span>
        </div>
      )}
    </div>
  );
}
