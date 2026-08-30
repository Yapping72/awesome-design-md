import { useState } from "react";
import { exportUrl } from "../api";
import RoundTripsTable from "../components/RoundTripsTable";
import TradesTable from "../components/TradesTable";

type View = "round-trips" | "fills";

export default function Trades() {
  const [view, setView] = useState<View>("round-trips");

  const exportHref =
    view === "round-trips"
      ? exportUrl("/api/trades/round-trips/export")
      : exportUrl("/api/trades/export");

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h2>Trades</h2>
        <a className="export-link" href={exportHref}>
          Export CSV
        </a>
      </div>
      <div className="period-toggle">
        <button
          className={view === "round-trips" ? "active" : ""}
          onClick={() => setView("round-trips")}
        >
          Round Trips
        </button>
        <button className={view === "fills" ? "active" : ""} onClick={() => setView("fills")}>
          Raw Fills
        </button>
      </div>
      {view === "round-trips" ? <RoundTripsTable /> : <TradesTable />}
    </div>
  );
}
