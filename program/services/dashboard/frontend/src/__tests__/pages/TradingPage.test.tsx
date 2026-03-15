import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import TradingPage from '../../pages/TradingPage';
import { useTradingStore } from '../../store/tradingStore';
import { useUIStore } from '../../store/uiStore';

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ connected: true })),
}));

describe('TradingPage', () => {
  beforeEach(() => {
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

  const renderPage = () =>
    render(
      <MemoryRouter>
        <TradingPage />
      </MemoryRouter>
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
});
