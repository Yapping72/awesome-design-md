import type {
  AggregationPeriod,
  DayPnl,
  EquityPoint,
  FxRate,
  PeriodPnl,
  Portfolio,
  RoundTripsPage,
  Summary,
  SymbolPerformance,
  TradeNote,
  TradesPage,
  UploadBatch,
  UploadResult,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// CSV exports are plain GET downloads (the server sets Content-Disposition),
// so components link straight to these URLs rather than fetching them.
export function exportUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function uploadReport(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResult>("/api/upload", { method: "POST", body: form });
}

export function getUploadBatches(): Promise<UploadBatch[]> {
  return request<UploadBatch[]>("/api/uploads");
}

export function deleteUploadBatch(batchId: number): Promise<{ deleted_fills: number }> {
  return request<{ deleted_fills: number }>(`/api/uploads/${batchId}`, { method: "DELETE" });
}

export function getCalendar(year: number, month: number): Promise<DayPnl[]> {
  return request<DayPnl[]>(`/api/pnl/calendar?year=${year}&month=${month}`);
}

export function getAggregate(
  period: AggregationPeriod,
  start?: string,
  end?: string
): Promise<PeriodPnl[]> {
  const params = new URLSearchParams({ period });
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  return request<PeriodPnl[]>(`/api/pnl/aggregate?${params.toString()}`);
}

export function getSummary(): Promise<Summary> {
  return request<Summary>("/api/pnl/summary");
}

export function getEquityCurve(): Promise<EquityPoint[]> {
  return request<EquityPoint[]>("/api/pnl/equity-curve");
}

export type SortDir = "asc" | "desc";

export function getTrades(params: {
  page?: number;
  pageSize?: number;
  symbol?: string;
  start?: string;
  end?: string;
  sortBy?: string;
  sortDir?: SortDir;
}): Promise<TradesPage> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("page_size", String(params.pageSize));
  if (params.symbol) qs.set("symbol", params.symbol);
  if (params.start) qs.set("start", params.start);
  if (params.end) qs.set("end", params.end);
  if (params.sortBy) qs.set("sort_by", params.sortBy);
  if (params.sortDir) qs.set("sort_dir", params.sortDir);
  return request<TradesPage>(`/api/trades?${qs.toString()}`);
}

export function getRoundTrips(params: {
  page?: number;
  pageSize?: number;
  symbol?: string;
  start?: string;
  end?: string;
  sortBy?: string;
  sortDir?: SortDir;
}): Promise<RoundTripsPage> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("page_size", String(params.pageSize));
  if (params.symbol) qs.set("symbol", params.symbol);
  if (params.start) qs.set("start", params.start);
  if (params.end) qs.set("end", params.end);
  if (params.sortBy) qs.set("sort_by", params.sortBy);
  if (params.sortDir) qs.set("sort_dir", params.sortDir);
  return request<RoundTripsPage>(`/api/trades/round-trips?${qs.toString()}`);
}

export function saveRoundTripNotes(
  roundTripId: string,
  notes: string,
  tags: string[]
): Promise<TradeNote> {
  return request<TradeNote>(`/api/trades/round-trips/${encodeURIComponent(roundTripId)}/notes`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes, tags }),
  });
}

export function getSymbolPerformance(): Promise<SymbolPerformance[]> {
  return request<SymbolPerformance[]>("/api/trades/by-symbol");
}

export function getUsdSgdRate(): Promise<FxRate> {
  return request<FxRate>("/api/fx/usdsgd");
}

export function getPortfolio(): Promise<Portfolio> {
  return request<Portfolio>("/api/portfolio");
}
