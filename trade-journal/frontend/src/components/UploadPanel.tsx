import { useEffect, useRef, useState } from "react";
import { deleteUploadBatch, getUploadBatches, uploadReport } from "../api";
import type { UploadBatch } from "../types";

interface Props {
  onUploaded: () => void;
}

export default function UploadPanel({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<{ kind: "success" | "error"; text: string } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [batches, setBatches] = useState<UploadBatch[]>([]);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function refreshBatches() {
    getUploadBatches()
      .then(setBatches)
      .catch(() => setBatches([]));
  }

  useEffect(refreshBatches, []);

  async function handleFile(file: File | undefined | null) {
    if (!file) return;
    setBusy(true);
    setStatus(null);
    try {
      const result = await uploadReport(file);
      setStatus({
        kind: "success",
        text: `Parsed ${result.parsed} fills — imported ${result.inserted} new, skipped ${result.skipped_duplicates} duplicates.`,
      });
      refreshBatches();
      onUploaded();
    } catch (err) {
      setStatus({ kind: "error", text: err instanceof Error ? err.message : "Upload failed" });
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(batch: UploadBatch) {
    if (!confirm(`Remove "${batch.filename}" (${batch.row_count} fill${batch.row_count === 1 ? "" : "s"})? This can't be undone.`)) {
      return;
    }
    setDeletingId(batch.id);
    try {
      await deleteUploadBatch(batch.id);
      refreshBatches();
      onUploaded();
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="panel">
      <h2>Import IBKR Activity Statement</h2>
      <div
        className={`upload-zone${dragging ? " dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
      >
        {busy ? "Uploading…" : "Drop your IBKR Activity Statement CSV here, or click to browse"}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
      {status && (
        <div className={`upload-status ${status.kind}`}>{status.text}</div>
      )}
      {batches.length > 0 && (
        <div className="upload-history">
          <div className="upload-history-title">Import History</div>
          {batches.map((b) => (
            <div className="upload-history-row" key={b.id}>
              <span className="upload-history-filename">{b.filename}</span>
              <span className="upload-history-meta">
                {new Date(b.uploaded_at).toLocaleString()} · {b.row_count} fill
                {b.row_count === 1 ? "" : "s"}
              </span>
              <button
                className="upload-history-delete"
                onClick={() => handleDelete(b)}
                disabled={deletingId === b.id}
              >
                {deletingId === b.id ? "Removing…" : "Remove"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
