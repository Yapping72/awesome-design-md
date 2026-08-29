import type { Summary } from "../types";

function fmt(n: number): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function pnlClass(n: number): string {
  return n > 0 ? "positive" : n < 0 ? "negative" : "";
}

export default function SummaryCards({ summary }: { summary: Summary }) {
  return (
    <div className="cards">
      <div className="card">
        <div className="label">Total P&amp;L</div>
        <div className={`value ${pnlClass(summary.total_pnl)}`}>${fmt(summary.total_pnl)}</div>
      </div>
      <div className="card">
        <div className="label">Win Rate</div>
        <div className="value">{summary.win_rate}%</div>
      </div>
      <div className="card">
        <div className="label">Closed Trades</div>
        <div className="value">{summary.closing_trades}</div>
      </div>
      <div className="card">
        <div className="label">Avg Win / Loss</div>
        <div className="value">
          <span className="positive">${fmt(summary.avg_win)}</span>
          {" / "}
          <span className="negative">${fmt(summary.avg_loss)}</span>
        </div>
      </div>
      <div className="card">
        <div className="label">Profit Factor</div>
        <div className="value">
          {summary.profit_factor !== null ? summary.profit_factor.toFixed(2) : "—"}
        </div>
      </div>
      <div className="card">
        <div className="label">Best / Worst Day</div>
        <div className="value" style={{ fontSize: 14 }}>
          <span className="positive">
            {summary.best_day ? `$${fmt(summary.best_day.pnl)}` : "—"}
          </span>
          <br />
          <span className="negative">
            {summary.worst_day ? `$${fmt(summary.worst_day.pnl)}` : "—"}
          </span>
        </div>
      </div>
    </div>
  );
}
