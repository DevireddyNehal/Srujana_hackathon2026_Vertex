export interface UserProfile {
  id: string;
  name: string;
  email: string;
  starting_balance: number;
  currency: string;
  timezone: string;
  is_demo: boolean;
  profile_description?: string;
  created_at: string;
}

export interface TradeRecord {
  id: string;
  user_id: string;
  symbol: string;
  asset_class: string;
  direction: "LONG" | "SHORT" | string;
  status: "OPEN" | "CLOSED" | string;
  is_demo?: boolean;
  entry_time: string;
  exit_time?: string | null;
  entry_price: number;
  exit_price?: number | null;
  quantity: number;
  contract_size: number;
  account_currency: string;
  stop_loss_price?: number | null;
  take_profit_price?: number | null;
  planned_risk_amount?: number | null;
  risk_pct_balance?: number | null;
  planned_rr_ratio?: number | null;
  realized_r_multiple?: number | null;
  gross_pnl: number;
  commission: number;
  other_fees: number;
  signed_swap_adjustment: number;
  net_pnl: number;
  strategy_or_setup?: string | null;
  trading_session?: string | null;
  tags?: string | null;
  notes?: string | null;
  emotional_state?: string | null;
  plan_followed?: boolean | number | null;
  mistakes_or_lessons?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface PaginatedTrades {
  items: TradeRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExtremeTrade {
  id: string;
  symbol: string;
  direction: string;
  exit_time: string;
  net_pnl: number;
  realized_r_multiple?: number | null;
}

export interface ExtremeDay {
  date: string;
  net_pnl: number;
  trades_count: number;
}

export interface PerformanceMetrics {
  user_id: string;
  user_name: string;
  account_currency: string;
  starting_balance: number;
  current_equity: number;
  total_closed_trades: number;
  winning_trades: number;
  losing_trades: number;
  breakeven_trades: number;
  win_rate: number | null;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  profit_factor: number | null;
  expectancy: number | null;
  average_win: number | null;
  average_loss: number | null;
  average_rr_ratio: number | null;
  total_trading_costs: number;
  average_holding_duration_seconds: number | null;
  best_trade?: ExtremeTrade | null;
  worst_trade?: ExtremeTrade | null;
  best_trading_day?: ExtremeDay | null;
  worst_trading_day?: ExtremeDay | null;
  realized_equity_curve_points: number;
  max_drawdown_currency: number;
  max_drawdown_pct: number;
  average_daily_pnl?: number | null;
  average_r_multiple?: number | null;
  max_consecutive_wins?: number;
  max_consecutive_losses?: number;
  profitable_days_count?: number;
  losing_days_count?: number;
  breakeven_days_count?: number;
  total_calendar_days_in_period?: number;
}

export interface DailyPnLPoint {
  date: string;
  closed_trades?: number;
  closed_trades_count?: number;
  gross_pnl: number;
  net_pnl: number;
  cumulative_pnl?: number;
  cumulative_net_pnl?: number;
  is_profitable?: boolean;
  is_winning_day?: boolean;
}

export interface BreakdownItem {
  dimension: string;
  item_name: string;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number | null;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  profit_factor: number | null;
  average_trade_pnl: number | null;
}
