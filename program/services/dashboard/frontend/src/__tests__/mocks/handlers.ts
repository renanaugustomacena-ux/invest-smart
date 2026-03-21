/**
 * MSW request handlers — real HTTP interception at the network layer.
 *
 * These replace vi.mock('../../api/client') across all page tests.
 * The actual fetchApi code runs for real; MSW intercepts fetch() calls
 * and returns recorded responses.
 */
import { http, HttpResponse } from 'msw';

// ─── Default Response Data ───────────────────────────────────────────────

export const defaultOverviewData = {
  signals_today: 5,
  daily_pnl: '150.50',
  total_trades_today: 3,
  win_rate: '66.7',
  open_positions: 2,
  drawdown_pct: '1.5',
  kill_switch_active: false,
  regime: 'TRENDING',
  redis_status: 'connected',
};

export const defaultSystemStatus = {
  database: { name: 'postgres', status: 'connected', latency_ms: 5 },
  redis: { name: 'redis', status: 'connected', latency_ms: 2 },
  services: [{ name: 'brain', status: 'connected', latency_ms: 15 }],
  uptime_seconds: 7200,
};

export const defaultRiskData = {
  daily_loss_pct: '0.500',
  drawdown_pct: '1.200',
  kill_switch_active: false,
  kill_switch_reason: undefined,
  open_positions: 2,
  max_positions: 5,
  symbols_exposed: ['EURUSD', 'GBPUSD'],
  maturity_state: 'PAPER',
  regime: 'TRENDING',
};

export const defaultMacroSnapshot = {
  snapshot: {
    vix_spot: '18.5',
    vix_regime: 'LOW',
    yield_slope: '0.45',
    curve_inverted: false,
    dxy_value: '104.5',
    dxy_trend: '1',
    recession_prob: '12.5',
    updated_at: '2024-01-15T10:00:00Z',
  },
};

export const defaultStrategyData = {
  data: [
    {
      strategy_name: 'coper',
      symbol: 'EURUSD',
      total_signals: 50,
      wins: 30,
      losses: 20,
      total_profit: '500.00',
      avg_confidence: '0.72',
      win_rate: '60.0',
    },
  ],
};

export const defaultEconomicEvents = {
  events: [
    {
      event_time: '2024-01-15T14:30:00Z',
      event_name: 'CPI Release',
      currency: 'USD',
      impact: 'high',
    },
  ],
};

export const defaultBlackouts = {
  blackouts: [
    {
      symbol: 'EURUSD',
      reason: 'ECB meeting',
      blackout_end: '2024-01-15T15:00:00Z',
    },
  ],
};

// ─── Default Handlers ────────────────────────────────────────────────────

export const handlers = [
  // System status (used by OverviewPage, ConfigPage)
  http.get('/api/system/status', () => {
    return HttpResponse.json(defaultSystemStatus);
  }),

  // Risk metrics (used by RiskPage which fetches /api/risk)
  http.get('/api/risk/metrics', () => {
    return HttpResponse.json(defaultRiskData);
  }),

  // Risk data (RiskPage component fetches /api/risk)
  http.get('/api/risk', () => {
    return HttpResponse.json(defaultRiskData);
  }),

  // System health (ConfigPage component fetches /api/system/health)
  http.get('/api/system/health', () => {
    return HttpResponse.json(defaultSystemStatus);
  }),

  // Risk kill switch toggle
  http.post('/api/risk/kill-switch', () => {
    return HttpResponse.json({ kill_switch_active: true });
  }),

  // Strategy performance
  http.get('/api/strategy/performance', () => {
    return HttpResponse.json(defaultStrategyData);
  }),

  // Strategy summary (used by StrategyPage component)
  http.get('/api/strategy/summary', () => {
    return HttpResponse.json(defaultStrategyData);
  }),

  // Macro snapshot
  http.get('/api/macro/snapshot', () => {
    return HttpResponse.json(defaultMacroSnapshot);
  }),

  // Macro VIX history
  http.get('/api/macro/vix', () => {
    return HttpResponse.json({ data: [] });
  }),

  // Macro DXY history
  http.get('/api/macro/dxy', () => {
    return HttpResponse.json({ data: [] });
  }),

  // Economic calendar
  http.get('/api/economic/upcoming', () => {
    return HttpResponse.json(defaultEconomicEvents);
  }),

  // Economic blackouts
  http.get('/api/economic/blackouts', () => {
    return HttpResponse.json(defaultBlackouts);
  }),

  // Market data symbols
  http.get('/api/market/symbols', () => {
    return HttpResponse.json({ symbols: ['EURUSD', 'GBPUSD'] });
  }),

  // Market data bars
  http.get('/api/market/bars', () => {
    return HttpResponse.json({ bars: [] });
  }),

  // Catch-all for any unhandled API requests
  http.get('/api/*path', () => {
    return HttpResponse.json({});
  }),
];
