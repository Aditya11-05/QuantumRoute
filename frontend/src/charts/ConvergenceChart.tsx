import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface ConvergenceChartProps {
  history: number[];
}

export default function ConvergenceChart({ history }: ConvergenceChartProps) {
  if (history.length === 0) {
    return <p className="text-sm text-[var(--qr-text-muted)]">No convergence data yet.</p>;
  }

  // Downsample for rendering performance if the history is very long.
  const maxPoints = 300;
  const step = Math.max(1, Math.floor(history.length / maxPoints));
  const data = history
    .filter((_, i) => i % step === 0)
    .map((energy, i) => ({ iteration: i * step, energy }));

  return (
    <ResponsiveContainer width="100%" height={140}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <XAxis
          dataKey="iteration"
          tick={{ fill: "var(--qr-text-muted)", fontSize: 10 }}
          stroke="var(--qr-border)"
        />
        <YAxis tick={{ fill: "var(--qr-text-muted)", fontSize: 10 }} stroke="var(--qr-border)" />
        <Tooltip
          contentStyle={{
            background: "var(--qr-panel-raised)",
            border: "1px solid var(--qr-border)",
            borderRadius: 6,
            fontSize: 12,
          }}
          labelFormatter={(v) => `iteration ${v}`}
          formatter={(value) => [typeof value === "number" ? value.toFixed(4) : String(value), "best energy"]}
        />
        <Line type="monotone" dataKey="energy" stroke="#2dd4bf" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
