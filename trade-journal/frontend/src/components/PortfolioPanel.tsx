import { useEffect, useState } from "react";
import { getPortfolio } from "../api";
import type { Portfolio } from "../types";

const REFRESH_MS = 30_000;

function fmt(n: number | null): string {
  return n === null ? "—" : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function pnlClass(n: number | null): string {
  if (n === null) return "";
  return n > 0 ? "positive" : n < 0 ? "negative" : "";
}

export default function PortfolioPanel({ refreshKey }: { refreshKey: number }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    function load() {
      getPortfolio()
        .then((res) => {
          if (!cancelled) setPortfolio(res);
        })
        .catch(() => {
          if (!cancelled) setPortfolio(null);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }

    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [refreshKey]);

  const hasQuoteGap =
    portfolio !== null &&
    portfolio.positions.length > 0 &&
    portfolio.positions.some((p) => p.last_price === null);

  return (
    <div className="panel">
      <h2>Open Positions</h2>
      {!loading && (!portfolio || portfolio.positions.length === 0) && (
        <div className="empty-state">No open positions.</div>
      )}
      {!loading && portfolio && portfolio.positions.length > 0 && (
        <>
          {hasQuoteGap && (
            <div className="quote-gap-note">
              Live quotes unavailable for one or more symbols right now — market value and
              unrealized P&amp;L show as “—” until the next refresh.
            </div>
          )}
          <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Cost</th>
                <th>Last Price</th>
                <th>Market Value</th>
                <th>Unrealized P/L</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((p) => (
                <tr key={p.symbol}>
                  <td>{p.symbol}</td>
                  <td>{p.quantity}</td>
                  <td>{p.avg_cost.toFixed(2)}</td>
                  <td>{p.last_price !== null ? p.last_price.toFixed(2) : "—"}</td>
                  <td>{fmt(p.market_value)}</td>
                  <td className={`pnl-cell ${pnlClass(p.unrealized_pnl)}`}>
                    {fmt(p.unrealized_pnl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <div className="portfolio-totals">
            <div>
              <span className="label">Market value</span>
              <span>
                ${fmt(portfolio.total_market_value_usd)}
                {portfolio.total_market_value_sgd !== null &&
                  ` (S$${fmt(portfolio.total_market_value_sgd)})`}
              </span>
            </div>
            <div>
              <span className="label">Unrealized P&amp;L</span>
              <span className={pnlClass(portfolio.total_unrealized_pnl_usd)}>
                ${fmt(portfolio.total_unrealized_pnl_usd)}
                {portfolio.total_unrealized_pnl_sgd !== null &&
                  ` (S$${fmt(portfolio.total_unrealized_pnl_sgd)})`}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
