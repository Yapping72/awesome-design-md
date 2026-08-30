import { useEffect, useState } from "react";
import { getRoundTrips } from "../api";
import type { RoundTrip } from "../types";

const PAGE_SIZE = 25;

function formatHoldDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(0)}m`;
  const hours = minutes / 60;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export default function RoundTripsTable() {
  const [page, setPage] = useState(1);
  const [symbol, setSymbol] = useState("");
  const [items, setItems] = useState<RoundTrip[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getRoundTrips({ page, pageSize: PAGE_SIZE, symbol: symbol || undefined })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [page, symbol]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <div className="filters">
        <input
          placeholder="Filter by symbol…"
          value={symbol}
          onChange={(e) => {
            setSymbol(e.target.value.toUpperCase());
            setPage(1);
          }}
        />
      </div>
      {!loading && items.length === 0 && (
        <div className="empty-state">
          No closed round trips yet — round trips appear once a position is fully or
          partially closed.
        </div>
      )}
      {!loading && items.length > 0 && (
        <>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Hold</th>
                <th>Commission</th>
                <th>P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {items.map((rt, idx) => (
                <tr key={`${rt.symbol}-${rt.exit_time}-${idx}`}>
                  <td>{rt.symbol}</td>
                  <td>
                    <span className={`side-badge ${rt.side}`}>{rt.side}</span>
                  </td>
                  <td>{rt.quantity}</td>
                  <td>{new Date(rt.entry_time).toLocaleString()}</td>
                  <td>{new Date(rt.exit_time).toLocaleString()}</td>
                  <td>{rt.entry_price.toFixed(2)}</td>
                  <td>{rt.exit_price.toFixed(2)}</td>
                  <td>{formatHoldDuration(rt.hold_seconds)}</td>
                  <td>{rt.commission.toFixed(2)}</td>
                  <td className={`pnl-cell ${rt.realized_pnl > 0 ? "positive" : rt.realized_pnl < 0 ? "negative" : ""}`}>
                    {rt.realized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>
              Page {page} of {totalPages} ({total} round trips)
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </>
  );
}
