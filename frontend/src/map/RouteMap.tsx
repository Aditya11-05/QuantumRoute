import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { RouteResponse } from "../types/api";

// Fix default marker icon paths (Leaflet + bundlers issue)
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface RouteMapProps {
  center: [number, number];
  source: [number, number] | null;
  destination: [number, number] | null;
  selectedRoute: RouteResponse | null;
  candidateRoutes: RouteResponse[];
  onMapClick: (lat: number, lon: number) => void;
}

export default function RouteMap({
  center,
  source,
  destination,
  selectedRoute,
  candidateRoutes,
  onMapClick,
}: RouteMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
    }).setView(center, 16);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    map.on("click", (e: L.LeafletMouseEvent) => {
      onMapClickRef.current(e.latlng.lat, e.latlng.lng);
    });

    layerGroupRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // Draw non-selected candidate routes first (faint, underneath)
    candidateRoutes.forEach((route, idx) => {
      if (selectedRoute && route.node_path.join(",") === selectedRoute.node_path.join(",")) return;
      const latlngs = route.coordinates.map(([lat, lon]) => [lat, lon] as [number, number]);
      L.polyline(latlngs, {
        color: "#f5a623",
        weight: 3,
        opacity: 0.35,
        dashArray: "4 6",
      })
        .bindTooltip(`Alt. route #${idx + 1} — cost ${route.total_cost.toFixed(3)}`)
        .addTo(layerGroup);
    });

    // Draw selected/optimal route on top, prominent
    if (selectedRoute && selectedRoute.coordinates.length > 0) {
      const latlngs = selectedRoute.coordinates.map(([lat, lon]) => [lat, lon] as [number, number]);
      L.polyline(latlngs, {
        color: "#2dd4bf",
        weight: 5,
        opacity: 0.95,
      })
        .bindTooltip(`Selected route — cost ${selectedRoute.total_cost.toFixed(3)}`)
        .addTo(layerGroup);
    }

    if (source) {
      L.circleMarker(source, {
        radius: 8,
        color: "#2dd4bf",
        fillColor: "#2dd4bf",
        fillOpacity: 1,
        weight: 2,
      })
        .bindTooltip("Source")
        .addTo(layerGroup);
    }
    if (destination) {
      L.circleMarker(destination, {
        radius: 8,
        color: "#f0524d",
        fillColor: "#f0524d",
        fillOpacity: 1,
        weight: 2,
      })
        .bindTooltip("Destination")
        .addTo(layerGroup);
    }
  }, [source, destination, selectedRoute, candidateRoutes]);

  useEffect(() => {
    mapRef.current?.setView(center, mapRef.current.getZoom());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center[0], center[1]]);

  return <div ref={containerRef} className="h-full w-full" />;
}
