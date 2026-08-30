import { useEffect, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getEquityCurve } from "../api";
import type { EquityPoint } from "../types";
import { useChartColors } from "../useChartColors";

export default function EquityCurveChart({ refreshKey }: { refreshKey: number }) {
  const [data, setData] = useState<EquityPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const colors = useChartColors();

  useEffect(() => {
    setLoading(true);
    getEquityCurve()
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const finalValue = data.length > 0 ? data[data.length - 1].cumulative_pnl : 0;
  const lineColor = finalValue >= 0 ? colors.green : colors.red;

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
              tick={{ fill: colors.textDim, fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(5)}
              axisLine={{ stroke: colors.panelBorder }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: colors.textDim, fontSize: 11 }}
              axisLine={{ stroke: colors.panelBorder }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: colors.panel, border: `1px solid ${colors.panelBorder}` }}
              labelStyle={{ color: colors.text }}
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
