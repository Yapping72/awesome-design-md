import { useEffect, useState } from "react";
import { getCalendar } from "../api";
import type { DayPnl } from "../types";

const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export default function Calendar({ refreshKey }: { refreshKey: number }) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-12
  const [days, setDays] = useState<DayPnl[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCalendar(year, month)
      .then(setDays)
      .catch(() => setDays([]))
      .finally(() => setLoading(false));
  }, [year, month, refreshKey]);

  function shiftMonth(delta: number) {
    let m = month + delta;
    let y = year;
    if (m > 12) {
      m = 1;
      y += 1;
    } else if (m < 1) {
      m = 12;
      y -= 1;
    }
    setMonth(m);
    setYear(y);
  }

  const pnlByDate = new Map(days.map((d) => [d.date, d]));
  const firstOfMonth = new Date(year, month - 1, 1);
  const leadingBlanks = firstOfMonth.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();

  const cells: (number | null)[] = [
    ...Array(leadingBlanks).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div className="panel">
      <h2>Calendar</h2>
      <div className="calendar-nav">
        <button onClick={() => shiftMonth(-1)}>‹</button>
        <div className="month-label">
          {MONTH_NAMES[month - 1]} {year}
        </div>
        <button onClick={() => shiftMonth(1)}>›</button>
      </div>
      {!loading && (
        <div className="calendar-grid">
          {DOW.map((d) => (
            <div className="dow" key={d}>
              {d}
            </div>
          ))}
          {cells.map((day, idx) => {
            if (day === null) {
              return <div className="day-cell empty" key={`blank-${idx}`} />;
            }
            const dateKey = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const entry = pnlByDate.get(dateKey);
            const cls = entry ? (entry.pnl > 0 ? "win" : entry.pnl < 0 ? "loss" : "") : "";
            return (
              <div className={`day-cell ${cls}`} key={dateKey}>
                <div className="day-num">{day}</div>
                {entry && (
                  <>
                    <div className="day-pnl">
                      {entry.pnl >= 0 ? "+" : ""}
                      {entry.pnl.toFixed(0)}
                    </div>
                    <div className="day-count">
                      {entry.trade_count} fill{entry.trade_count === 1 ? "" : "s"}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
