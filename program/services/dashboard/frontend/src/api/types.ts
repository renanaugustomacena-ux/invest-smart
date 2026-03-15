export interface ServiceHealth {
  name: string;
  status: 'connected' | 'disconnected';
  latency_ms?: number | null;
  error?: string | null;
}

export interface OverviewKPIs {
  signals_today: number;
  signals_per_hour: number;
  daily_pnl: string;
  daily_pnl_pct: string;
  open_positions: number;
  drawdown_pct: string;
  kill_switch_active: boolean;
  win_rate: string;
  total_trades_today: number;
}

export interface OverviewResponse {
  kpis: OverviewKPIs;
  services: ServiceHealth[];
  recent_signals: TradingSignal[];
  timestamp: string;
}

export interface TradingSignal {
  signal_id: string;
  created_at: string;
  symbol: string;
  direction: string;
  confidence: string;
  suggested_lots?: string;
  stop_loss?: string;
  take_profit?: string;
  model_version?: string;
  regime?: string;
  source_tier?: string;
  reasoning?: string;
}

export interface TradeExecution {
  id: number;
  signal_id?: string;
  executed_at: string;
  symbol: string;
  direction: string;
  executed_price?: string;
  quantity?: string;
  status: string;
  profit?: string;
}

export interface RiskMetrics {
  daily_loss_pct: string;
  drawdown_pct: string;
  kill_switch_active: boolean;
  kill_switch_reason?: string;
  open_positions: number;
  max_positions: number;
  symbols_exposed: string[];
  maturity_state?: string;
  regime?: string;
}

export interface OHLCVBar {
  time: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface MacroSnapshot {
  vix_spot?: string;
  vix_regime?: string;
  yield_slope?: string;
  curve_inverted?: boolean;
  dxy_value?: string;
  dxy_trend?: string;
  recession_prob?: string;
}

export interface SystemStatus {
  database: ServiceHealth;
  redis: ServiceHealth;
  services: ServiceHealth[];
  uptime_seconds?: number;
}
