import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { exportUrl, getAggregate } from "../api";
import type { AggregationPeriod, PeriodPnl } from "../types";
import { useChartColors } from "../useChartColors";

const PERIODS: { value: AggregationPeriod; label: string }[] = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

export default function AggregationChart({ refreshKey }: { refreshKey: number }) {
  const [period, setPeriod] = useState<AggregationPeriod>("day");
  const [data, setData] = useState<PeriodPnl[]>([]);
  const [loading, setLoading] = useState(true);
  const colors = useChartColors();

  useEffect(() => {
    setLoading(true);
    getAggregate(period)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [period, refreshKey]);

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h2>P&amp;L by {PERIODS.find((p) => p.value === period)?.label}</h2>
        <a className="export-link" href={exportUrl("/api/pnl/export")}>
          Export Daily P&amp;L CSV
        </a>
      </div>
      <div className="period-toggle">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            className={period === p.value ? "active" : ""}
            onClick={() => setPeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>
      {!loading && data.length === 0 && (
        <div className="empty-state">No trades imported yet.</div>
      )}
      {!loading && data.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data}>
            <XAxis
              dataKey="period"
              tick={{ fill: colors.textDim, fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(0, 10)}
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
              formatter={(value: number) => [`$${value.toFixed(2)}`, "P&L"]}
            />
            <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.period}
                  fill={entry.pnl >= 0 ? colors.green : colors.red}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
