import { useState } from "react";
import RoundTripsTable from "../components/RoundTripsTable";
import TradesTable from "../components/TradesTable";

type View = "round-trips" | "fills";

export default function Trades() {
  const [view, setView] = useState<View>("round-trips");

  return (
    <div className="panel">
      <h2>Trades</h2>
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
