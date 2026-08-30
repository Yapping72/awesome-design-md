import { Fragment, useEffect, useState } from "react";
import { getRoundTrips, saveRoundTripNotes, type SortDir } from "../api";
import type { RoundTrip } from "../types";
import SortableTh from "./SortableTh";

const PAGE_SIZE = 25;

function formatHoldDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(0)}m`;
  const hours = minutes / 60;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

function NoteEditor({
  trip,
  onSaved,
  onCancel,
}: {
  trip: RoundTrip;
  onSaved: (updated: { notes: string | null; tags: string[] }) => void;
  onCancel: () => void;
}) {
  const [notes, setNotes] = useState(trip.notes ?? "");
  const [tagsInput, setTagsInput] = useState(trip.tags.join(", "));
  const [saving, setSaving] = useState(false);

  function handleSave() {
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    setSaving(true);
    saveRoundTripNotes(trip.round_trip_id, notes, tags)
      .then((res) => onSaved({ notes: res.notes, tags: res.tags }))
      .finally(() => setSaving(false));
  }

  return (
    <tr className="note-editor-row">
      <td colSpan={11}>
        <div className="note-editor">
          <textarea
            placeholder="What was the setup? What went right or wrong?"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
          <input
            placeholder="Tags, comma separated (e.g. breakout, earnings, revenge-trade)"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
          />
          <div className="note-editor-actions">
            <button className="primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button onClick={onCancel} disabled={saving}>
              Cancel
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function RoundTripsTable() {
  const [page, setPage] = useState(1);
  const [symbol, setSymbol] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sortBy, setSortBy] = useState("exit_time");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [items, setItems] = useState<RoundTrip[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getRoundTrips({
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

  function applyLocalUpdate(roundTripId: string, updated: { notes: string | null; tags: string[] }) {
    setItems((prev) =>
      prev.map((rt) => (rt.round_trip_id === roundTripId ? { ...rt, ...updated } : rt))
    );
    setEditingId(null);
  }

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
        <div className="empty-state">
          No closed round trips yet — round trips appear once a position is fully or
          partially closed.
        </div>
      )}
      {!loading && items.length > 0 && (
        <>
          <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <SortableTh label="Symbol" sortKey="symbol" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Side" sortKey="side" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Qty" sortKey="quantity" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Entry" sortKey="entry_time" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Exit" sortKey="exit_time" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Entry Price" sortKey="entry_price" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Exit Price" sortKey="exit_price" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Hold" sortKey="hold_seconds" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="Commission" sortKey="commission" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <SortableTh label="P&L" sortKey="realized_pnl" activeSortBy={sortBy} activeSortDir={sortDir} onSort={handleSort} />
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {items.map((rt) => (
                <Fragment key={rt.round_trip_id}>
                  <tr>
                    <td>{rt.symbol}</td>
                    <td>
                      <span className={`side-badge ${rt.side}`}>{rt.side}</span>
                    </td>
                    <td>{rt.quantity}</td>
                    <td>{new Date(rt.entry_time).toLocaleString()}</td>
                    <td>{new Date(rt.exit_time).toLocaleString()}</td>
                    <td>{rt.entry_price.toFixed(2)}</td>
                    <td>{rt.exit_price.toFixed(2)}</td>
                    <td>{formatHoldDuration(rt.hold_seconds)}</td>
                    <td>{rt.commission.toFixed(2)}</td>
                    <td className={`pnl-cell ${rt.realized_pnl > 0 ? "positive" : rt.realized_pnl < 0 ? "negative" : ""}`}>
                      {rt.realized_pnl.toFixed(2)}
                    </td>
                    <td>
                      <button
                        className="notes-trigger"
                        onClick={() =>
                          setEditingId(editingId === rt.round_trip_id ? null : rt.round_trip_id)
                        }
                      >
                        {rt.tags.length > 0 ? (
                          <span className="tag-pills">
                            {rt.tags.map((tag) => (
                              <span className="tag-pill" key={tag}>
                                {tag}
                              </span>
                            ))}
                          </span>
                        ) : rt.notes ? (
                          <span className="note-preview">{rt.notes.slice(0, 40)}</span>
                        ) : (
                          <span className="note-preview muted">+ Add note</span>
                        )}
                      </button>
                    </td>
                  </tr>
                  {editingId === rt.round_trip_id && (
                    <NoteEditor
                      key={`${rt.round_trip_id}-editor`}
                      trip={rt}
                      onSaved={(updated) => applyLocalUpdate(rt.round_trip_id, updated)}
                      onCancel={() => setEditingId(null)}
                    />
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
          </div>
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>
              Page {page} of {totalPages} ({total} round trips)
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
