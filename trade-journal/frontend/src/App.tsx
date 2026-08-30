import { useState } from "react";
import FxTicker from "./components/FxTicker";
import ThemeToggle from "./components/ThemeToggle";
import Dashboard from "./pages/Dashboard";
import TradesPage from "./pages/Trades";

type Tab = "dashboard" | "trades";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <>
      <header className="app-header">
        <div>
          <h1>Trade Journal</h1>
          <div className="subtitle">IBKR activity import &amp; P&amp;L journal</div>
        </div>
        <div className="header-right">
          <FxTicker />
          <ThemeToggle />
          <nav className="tabs">
            <button
              className={tab === "dashboard" ? "active" : ""}
              onClick={() => setTab("dashboard")}
            >
              Dashboard
            </button>
            <button
              className={tab === "trades" ? "active" : ""}
              onClick={() => setTab("trades")}
            >
              Trades
            </button>
          </nav>
        </div>
      </header>

      {tab === "dashboard" ? (
        <Dashboard onDataChanged={() => setRefreshKey((k) => k + 1)} />
      ) : (
        <TradesPage key={refreshKey} />
      )}
    </>
  );
}
