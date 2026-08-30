import { useEffect, useState } from "react";
import { getSymbolPerformance } from "../api";
import type { SymbolPerformance } from "../types";

export default function SymbolPerformanceTable({ refreshKey }: { refreshKey: number }) {
  const [rows, setRows] = useState<SymbolPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSymbolPerformance()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  return (
    <div className="panel">
      <h2>Performance by Symbol</h2>
      {!loading && rows.length === 0 && (
        <div className="empty-state">No closed round trips yet.</div>
      )}
      {!loading && rows.length > 0 && (
        <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Trades</th>
              <th>Win Rate</th>
              <th>Avg P&amp;L</th>
              <th>Total P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol}>
                <td>{r.symbol}</td>
                <td>
                  {r.trade_count} ({r.wins}W / {r.losses}L)
                </td>
                <td>{r.win_rate.toFixed(1)}%</td>
                <td className={`pnl-cell ${r.avg_pnl > 0 ? "positive" : r.avg_pnl < 0 ? "negative" : ""}`}>
                  {r.avg_pnl.toFixed(2)}
                </td>
                <td className={`pnl-cell ${r.total_pnl > 0 ? "positive" : r.total_pnl < 0 ? "negative" : ""}`}>
                  {r.total_pnl.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
