import { useEffect, useState } from "react";
import { getSummary } from "../api";
import AggregationChart from "../components/AggregationChart";
import Calendar from "../components/Calendar";
import SummaryCards from "../components/SummaryCards";
import UploadPanel from "../components/UploadPanel";
import type { Summary } from "../types";

export default function Dashboard({ onDataChanged }: { onDataChanged: () => void }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  function refresh() {
    setRefreshKey((k) => k + 1);
    onDataChanged();
  }

  useEffect(() => {
    getSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }, [refreshKey]);

  return (
    <>
      <UploadPanel onUploaded={refresh} />
      {summary && <SummaryCards summary={summary} />}
      <Calendar refreshKey={refreshKey} />
      <AggregationChart refreshKey={refreshKey} />
    </>
  );
}
