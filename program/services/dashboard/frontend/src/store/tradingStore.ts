import { create } from 'zustand';

export interface OverviewData {
  signals_today: number;
  daily_pnl: string;
  total_trades_today: number;
  win_rate: string;
  open_positions: number;
  drawdown_pct: string;
  kill_switch_active: boolean;
  regime: string | null;
  redis_status: string;
}

export interface SignalRow {
  signal_id: string;
  symbol: string;
  direction: string;
  confidence: string;
  source_tier: string | null;
  regime: string | null;
  created_at: string;
}

export interface PositionRow {
  symbol: string;
  side: string;
  quantity: string;
  avg_price: string;
  current_price?: string;
  unrealized_pnl?: string;
}

interface TradingState {
  overview: OverviewData | null;
  signals: SignalRow[];
  positions: PositionRow[];
  regime: string | null;
  wsConnected: boolean;

  setOverview: (data: OverviewData) => void;
  setTradingData: (signals: SignalRow[], positions: PositionRow[], regime: string | null) => void;
  setWsConnected: (c: boolean) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  overview: null,
  signals: [],
  positions: [],
  regime: null,
  wsConnected: false,

  setOverview: (data) => set({ overview: data }),

  setTradingData: (signals, positions, regime) =>
    set({ signals, positions, regime }),

  setWsConnected: (c) => set({ wsConnected: c }),
}));
