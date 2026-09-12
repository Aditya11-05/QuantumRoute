import type { TrafficMapRequest, TrafficMapResponse } from "../types/trafficMap";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getTrafficMap(
  payload: TrafficMapRequest,
): Promise<TrafficMapResponse> {
  const response = await fetch(`${BASE_URL}/traffic/map`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`POST /traffic/map failed: ${response.status} ${body}`);
  }

  return response.json() as Promise<TrafficMapResponse>;
}
