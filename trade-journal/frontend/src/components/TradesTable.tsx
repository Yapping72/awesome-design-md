import { useEffect, useState } from "react";
import { getTrades } from "../api";
import type { Trade } from "../types";

const PAGE_SIZE = 25;

export default function TradesTable() {
  const [page, setPage] = useState(1);
  const [symbol, setSymbol] = useState("");
  const [items, setItems] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getTrades({ page, pageSize: PAGE_SIZE, symbol: symbol || undefined })
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
        <div className="empty-state">No trades found.</div>
      )}
      {!loading && items.length > 0 && (
        <>
          <table>
            <thead>
              <tr>
                <th>Date/Time</th>
                <th>Symbol</th>
                <th>Category</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Commission</th>
                <th>Realized P/L</th>
                <th>Net P/L</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t) => (
                <tr key={t.id}>
                  <td>{new Date(t.trade_datetime).toLocaleString()}</td>
                  <td>{t.symbol}</td>
                  <td>{t.asset_category ?? "—"}</td>
                  <td>{t.quantity}</td>
                  <td>{t.price.toFixed(2)}</td>
                  <td>{(t.commission ?? 0).toFixed(2)}</td>
                  <td className={`pnl-cell ${t.realized_pnl > 0 ? "positive" : t.realized_pnl < 0 ? "negative" : ""}`}>
                    {t.realized_pnl.toFixed(2)}
                  </td>
                  <td className={`pnl-cell ${t.net_pnl > 0 ? "positive" : t.net_pnl < 0 ? "negative" : ""}`}>
                    {t.net_pnl.toFixed(2)}
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
              Page {page} of {totalPages} ({total} trades)
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
