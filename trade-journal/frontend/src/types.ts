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

export interface UploadBatch {
  id: number;
  filename: string;
  row_count: number;
  uploaded_at: string;
}

export type AggregationPeriod = "day" | "week" | "month";

export interface RoundTrip {
  round_trip_id: string;
  symbol: string;
  side: "long" | "short";
  quantity: number;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  commission: number;
  realized_pnl: number;
  hold_seconds: number;
  notes: string | null;
  tags: string[];
}

export interface SymbolPerformance {
  symbol: string;
  trade_count: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface EquityPoint {
  date: string;
  pnl: number;
  cumulative_pnl: number;
}

export interface TradeNote {
  round_trip_id: string;
  notes: string | null;
  tags: string[];
}

export interface RoundTripsPage {
  total: number;
  page: number;
  page_size: number;
  items: RoundTrip[];
}

export interface FxRate {
  pair: string;
  rate: number | null;
}

export interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  currency: string | null;
  asset_category: string | null;
  last_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
}

export interface Portfolio {
  positions: Position[];
  usd_sgd_rate: number | null;
  total_market_value_usd: number;
  total_unrealized_pnl_usd: number;
  total_market_value_sgd: number | null;
  total_unrealized_pnl_sgd: number | null;
}
