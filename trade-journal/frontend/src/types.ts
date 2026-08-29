export interface DayPnl {
  date: string;
  pnl: number;
  trade_count: number;
}

export interface PeriodPnl {
  period: string;
  pnl: number;
  trade_count: number;
}

export interface Summary {
  total_pnl: number;
  total_trades: number;
  closing_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number | null;
  best_day: DayPnl | null;
  worst_day: DayPnl | null;
}

export interface Trade {
  id: number;
  symbol: string;
  asset_category: string | null;
  currency: string | null;
  trade_datetime: string;
  trade_date: string;
  quantity: number;
  price: number;
  proceeds: number | null;
  commission: number | null;
  realized_pnl: number;
  net_pnl: number;
  code: string | null;
}

export interface TradesPage {
  total: number;
  page: number;
  page_size: number;
  items: Trade[];
}

export interface UploadResult {
  parsed: number;
  inserted: number;
  skipped_duplicates: number;
}

export type AggregationPeriod = "day" | "week" | "month";
