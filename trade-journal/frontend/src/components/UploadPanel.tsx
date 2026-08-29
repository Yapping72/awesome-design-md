import { useRef, useState } from "react";
import { uploadReport } from "../api";

interface Props {
  onUploaded: () => void;
}

export default function UploadPanel({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<{ kind: "success" | "error"; text: string } | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
      onUploaded();
    } catch (err) {
      setStatus({ kind: "error", text: err instanceof Error ? err.message : "Upload failed" });
    } finally {
      setBusy(false);
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
    </div>
  );
}
