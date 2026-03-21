import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { installFakeWebSocket, type WebSocketManager } from '../mocks/websocket';
import TradingPage from '../../pages/TradingPage';
import { useTradingStore } from '../../store/tradingStore';
import { useUIStore } from '../../store/uiStore';

let wsManager: WebSocketManager;

describe('TradingPage', () => {
  beforeEach(() => {
    wsManager = installFakeWebSocket();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useTradingStore.setState({
      overview: null,
      signals: [],
      positions: [],
      regime: null,
      wsConnected: false,
    });
    useUIStore.setState({ toasts: [], notifications: [], unreadCount: 0 });
  });

  afterEach(() => {
    wsManager.cleanup();
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <TradingPage />
      </MemoryRouter>,
    );

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('Trading')).toBeInTheDocument();
  });

  it('shows empty state for signals', () => {
    renderPage();
    expect(screen.getByText('No signals yet')).toBeInTheDocument();
  });

  it('shows empty state for positions', () => {
    renderPage();
    expect(screen.getByText('No open positions')).toBeInTheDocument();
  });

  it('renders signals table with data', () => {
    useTradingStore.setState({
      signals: [
        { signal_id: 's1', symbol: 'EURUSD', direction: 'BUY', confidence: '0.85', source_tier: 'tier1', regime: 'TRENDING', created_at: '2024-01-15T10:00:00Z' },
      ],
    });
    renderPage();
    expect(screen.getByText('EURUSD')).toBeInTheDocument();
    expect(screen.getByText('BUY')).toBeInTheDocument();
  });

  it('renders positions table with data', () => {
    useTradingStore.setState({
      positions: [
        { symbol: 'GBPUSD', side: 'LONG', quantity: '0.1', avg_price: '1.25', unrealized_pnl: '50.00' },
      ],
    });
    renderPage();
    expect(screen.getByText('GBPUSD')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
  });

  it('renders WS connected status after open', async () => {
    renderPage();
    // Before WS open, component should show connecting state
    wsManager.simulateOpen();

    // After WS open, the store should reflect connected = true
    await waitFor(() => {
      const state = useTradingStore.getState();
      expect(state.wsConnected).toBe(true);
    });
  });

  it('updates signals from WS message', async () => {
    renderPage();
    wsManager.simulateOpen();
    wsManager.simulateMessage({
      type: 'trading',
      data: {
        recent_signals: [
          { signal_id: 'ws1', symbol: 'USDJPY', direction: 'SELL', confidence: '0.92', source_tier: 'tier2', regime: 'MEAN_REVERTING', created_at: '2024-01-15T11:30:00Z' },
        ],
        positions: [
          { symbol: 'AUDUSD', side: 'LONG', quantity: '0.5', avg_price: '0.6500', unrealized_pnl: '25.00' },
        ],
        regime: 'MEAN_REVERTING',
      },
    });

    await waitFor(() => {
      expect(screen.getByText('USDJPY')).toBeInTheDocument();
    });
    expect(screen.getByText('SELL')).toBeInTheDocument();
    expect(screen.getByText('AUDUSD')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
  });
});
