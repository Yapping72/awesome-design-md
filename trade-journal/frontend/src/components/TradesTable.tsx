import { useEffect, useState } from "react";
import { getTrades, type SortDir } from "../api";
import type { Trade } from "../types";
import SortableTh from "./SortableTh";

const PAGE_SIZE = 25;

export default function TradesTable() {
  const [page, setPage] = useState(1);
  const [symbol, setSymbol] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sortBy, setSortBy] = useState("trade_datetime");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [items, setItems] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getTrades({
      page,
      pageSize: PAGE_SIZE,
      symbol: symbol || undefined,
      start: start || undefined,
      end: end || undefined,
      sortBy,
      sortDir,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [page, symbol, start, end, sortBy, sortDir]);

  function handleSort(key: string) {
    if (key === sortBy) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
    setPage(1);
  }

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
        <input
          type="date"
          value={start}
          onChange={(e) => {
            setStart(e.target.value);
            setPage(1);
          }}
        />
        <span className="filters-sep">to</span>
        <input
          type="date"
          value={end}
          onChange={(e) => {
            setEnd(e.target.value);
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
                <SortableTh label="Date/Time" sortKey="trade_datetime" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Symbol" sortKey="symbol" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <th>Category</th>
                <SortableTh label="Qty" sortKey="quantity" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Price" sortKey="price" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Commission" sortKey="commission" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Realized P/L" sortKey="realized_pnl" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Net P/L" sortKey="net_pnl" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
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
