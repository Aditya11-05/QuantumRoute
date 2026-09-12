import type {
  AnalysisRequest,
  RouteAnalysisResponse,
} from "../types/api";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getRouteAnalysis(
  request: AnalysisRequest,
): Promise<RouteAnalysisResponse> {
  const res = await fetch(`${BASE_URL}/route/analysis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `POST /route/analysis failed: ${res.status} ${body}`,
    );
  }

  return res.json() as Promise<RouteAnalysisResponse>;
}
