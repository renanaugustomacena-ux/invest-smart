import { describe, it, expect, beforeEach } from 'vitest';
import { useTradingStore } from '../../store/tradingStore';
import type { OverviewData, SignalRow, PositionRow } from '../../store/tradingStore';

describe('tradingStore', () => {
  beforeEach(() => {
    useTradingStore.setState({
      overview: null,
      signals: [],
      positions: [],
      regime: null,
      wsConnected: false,
    });
  });

  it('setOverview updates overview data', () => {
    const overview: OverviewData = {
      signals_today: 5,
      daily_pnl: '150.00',
      total_trades_today: 3,
      win_rate: '66.7',
      open_positions: 2,
      drawdown_pct: '1.5',
      kill_switch_active: false,
      regime: 'TRENDING',
      redis_status: 'connected',
    };
    useTradingStore.getState().setOverview(overview);
    expect(useTradingStore.getState().overview).toEqual(overview);
  });

  it('setTradingData updates signals, positions, and regime', () => {
    const signals: SignalRow[] = [{
      signal_id: 's1',
      symbol: 'EURUSD',
      direction: 'BUY',
      confidence: '0.85',
      source_tier: 'tier1',
      regime: 'TRENDING',
      created_at: '2024-01-15',
    }];
    const positions: PositionRow[] = [{
      symbol: 'EURUSD',
      side: 'BUY',
      quantity: '0.1',
      avg_price: '1.0850',
    }];
    useTradingStore.getState().setTradingData(signals, positions, 'TRENDING');

    const state = useTradingStore.getState();
    expect(state.signals).toEqual(signals);
    expect(state.positions).toEqual(positions);
    expect(state.regime).toBe('TRENDING');
  });

  it('setWsConnected updates connection state', () => {
    useTradingStore.getState().setWsConnected(true);
    expect(useTradingStore.getState().wsConnected).toBe(true);
  });
});
