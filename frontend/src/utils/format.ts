export const TRAFFIC_SCENARIOS: { value: string; label: string; hint: string }[] = [
  { value: "low", label: "Low", hint: "Free-flowing" },
  { value: "medium", label: "Medium", hint: "Typical midday" },
  { value: "heavy", label: "Heavy", hint: "Congested" },
  { value: "peak", label: "Peak hour", hint: "Rush hour" },
  { value: "incident", label: "Incident", hint: "Simulated accident" },
  { value: "closure", label: "Road closure", hint: "Segments blocked" },
];

export function formatDuration(seconds: number): string {
  if (!isFinite(seconds)) return "—";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return `${h}h ${rem}m`;
}

export function formatDistance(meters: number): string {
  if (!isFinite(meters)) return "—";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(2)} km`;
}
