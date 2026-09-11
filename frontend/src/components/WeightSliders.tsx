import type { OptimizationWeights } from "../types/api";

interface WeightSlidersProps {
  weights: OptimizationWeights;
  onChange: (weights: OptimizationWeights) => void;
}

const ROWS: { key: keyof OptimizationWeights; label: string }[] = [
  { key: "travel_time", label: "Travel time" },
  { key: "congestion", label: "Congestion" },
  { key: "distance", label: "Distance" },
  { key: "fuel", label: "Fuel" },
  { key: "intersection", label: "Intersections" },
  { key: "incident", label: "Incidents" },
];

export default function WeightSliders({ weights, onChange }: WeightSlidersProps) {
  const total = ROWS.reduce((sum, r) => sum + weights[r.key], 0) || 1;

  return (
    <div className="flex flex-col gap-3">
      {ROWS.map((row) => {
        const pct = Math.round((weights[row.key] / total) * 100);
        return (
          <div key={row.key}>
            <div className="flex items-baseline justify-between text-xs mb-1">
              <span className="text-[var(--qr-text-muted)]">{row.label}</span>
              <span className="font-mono-qr text-[var(--qr-cyan)]">{pct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={weights[row.key]}
              onChange={(e) => onChange({ ...weights, [row.key]: Number(e.target.value) })}
              className="w-full accent-[#2dd4bf] h-1.5"
              aria-label={`${row.label} weight`}
            />
          </div>
        );
      })}
    </div>
  );
}
