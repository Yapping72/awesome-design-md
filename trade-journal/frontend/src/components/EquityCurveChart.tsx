import { useEffect, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getEquityCurve } from "../api";
import type { EquityPoint } from "../types";

export default function EquityCurveChart({ refreshKey }: { refreshKey: number }) {
  const [data, setData] = useState<EquityPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getEquityCurve()
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const finalValue = data.length > 0 ? data[data.length - 1].cumulative_pnl : 0;
  const lineColor = finalValue >= 0 ? "#3fb950" : "#f85149";

  return (
    <div className="panel">
      <h2>Equity Curve</h2>
      {!loading && data.length === 0 && (
        <div className="empty-state">No trades imported yet.</div>
      )}
      {!loading && data.length > 0 && (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={0.3} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fill: "#8b949e", fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(5)}
              axisLine={{ stroke: "#262c36" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#8b949e", fontSize: 11 }}
              axisLine={{ stroke: "#262c36" }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: "#161b22", border: "1px solid #262c36" }}
              labelStyle={{ color: "#e6edf3" }}
              formatter={(value: number) => [`$${value.toFixed(2)}`, "Cumulative P&L"]}
            />
            <Area
              type="monotone"
              dataKey="cumulative_pnl"
              stroke={lineColor}
              strokeWidth={2}
              fill="url(#equityFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
