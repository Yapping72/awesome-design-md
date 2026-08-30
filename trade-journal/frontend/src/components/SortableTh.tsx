import type { SortDir } from "../api";

export default function SortableTh({
  label,
  sortKey,
  activeSortBy,
  activeSortDir,
  onSort,
}: {
  label: string;
  sortKey: string;
  activeSortBy: string;
  activeSortDir: SortDir;
  onSort: (key: string) => void;
}) {
  const active = activeSortBy === sortKey;
  return (
    <th className="sortable-th" onClick={() => onSort(sortKey)}>
      {label}
      <span className={`sort-arrow${active ? " active" : ""}`}>
        {active ? (activeSortDir === "asc" ? "▲" : "▼") : "↕"}
      </span>
    </th>
  );
}
