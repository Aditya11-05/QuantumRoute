import { useEffect, useState } from "react";
import { predictCongestion } from "../services/api";
import type { TrafficPredictResponse } from "../types/api";

export default function AiPredictionPanel() {
  const [hour, setHour] = useState(new Date().getHours());
  const [roadType, setRoadType] = useState("primary");
  const [prediction, setPrediction] = useState<TrafficPredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    predictCongestion({ hour, day_of_week: new Date().getDay(), road_type: roadType, occupancy: 0.5 })
      .then((res) => {
        if (!cancelled) {
          setPrediction(res);
          setError(null);
        }
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [hour, roadType]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        <label className="flex-1 text-xs text-[var(--qr-text-muted)]">
          Hour of day
          <input
            type="range"
            min={0}
            max={23}
            value={hour}
            onChange={(e) => setHour(Number(e.target.value))}
            className="w-full accent-[#2dd4bf] mt-1"
          />
          <div className="font-mono-qr text-[var(--qr-cyan)]">{String(hour).padStart(2, "0")}:00</div>
        </label>
        <label className="flex-1 text-xs text-[var(--qr-text-muted)]">
          Road type
          <select
            value={roadType}
            onChange={(e) => setRoadType(e.target.value)}
            className="w-full mt-1 bg-[var(--qr-panel-raised)] border border-[var(--qr-border)] rounded px-2 py-1 text-sm text-[var(--qr-text)]"
          >
            <option value="residential">Residential</option>
            <option value="tertiary">Tertiary</option>
            <option value="secondary">Secondary</option>
            <option value="primary">Primary</option>
          </select>
        </label>
      </div>

      {error && <p className="text-xs text-[var(--qr-red)]">{error}</p>}

      {prediction && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-[var(--qr-text-muted)]">
              Predicted congestion
            </div>
            <div className="font-mono-qr text-lg text-[var(--qr-text)]">
              {(prediction.predicted_congestion_level * 100).toFixed(0)}%
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wide text-[var(--qr-text-muted)]">Model</div>
            <div className="text-sm text-[var(--qr-text)]">
              {prediction.model_loaded ? "LightGBM (trained)" : "Not loaded — placeholder"}
            </div>
          </div>
        </div>
      )}
      <p className="text-xs text-[var(--qr-text-muted)] leading-relaxed">
        {prediction?.model_disclaimer}
      </p>
    </div>
  );
}
