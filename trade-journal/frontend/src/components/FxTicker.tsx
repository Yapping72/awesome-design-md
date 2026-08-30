import { useEffect, useState } from "react";
import { getUsdSgdRate } from "../api";

const REFRESH_MS = 30_000;

export default function FxTicker() {
  const [rate, setRate] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    function load() {
      getUsdSgdRate()
        .then((res) => {
          if (cancelled) return;
          setRate(res.rate);
          setFailed(res.rate === null);
        })
        .catch(() => {
          if (!cancelled) setFailed(true);
        });
    }

    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div
      className="fx-ticker"
      title={failed ? "Live rate unavailable right now" : "Live USD/SGD, refreshes every 30s"}
    >
      <span className="fx-label">USD/SGD</span>
      <span className="fx-value">{rate !== null ? rate.toFixed(4) : "—"}</span>
    </div>
  );
}
