import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Header from '../../../components/layout/Header';
import { useUIStore } from '../../../store/uiStore';
import { useTradingStore } from '../../../store/tradingStore';

describe('Header', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({
      theme: 'dark',
      toasts: [],
      notifications: [],
      unreadCount: 0,
      paletteOpen: false,
    });
    useTradingStore.setState({ overview: null, wsConnected: false });
  });

  const renderHeader = (props = {}) =>
    render(
      <MemoryRouter>
        <Header {...props} />
      </MemoryRouter>
    );

  it('renders MONEYMAKER brand', () => {
    renderHeader();
    expect(screen.getByText('MONEYMAKER')).toBeInTheDocument();
  });

  it('shows Reconnecting when not connected', () => {
    renderHeader({ wsConnected: false });
    expect(screen.getByText('Reconnecting…')).toBeInTheDocument();
  });

  it('shows Live when connected', () => {
    renderHeader({ wsConnected: true });
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('shows daily PnL from store', () => {
    useTradingStore.setState({
      overview: {
        signals_today: 0,
        daily_pnl: '150.50',
        total_trades_today: 0,
        win_rate: '0',
        open_positions: 0,
        drawdown_pct: '0',
        kill_switch_active: false,
        regime: null,
        redis_status: 'connected',
      },
    });
    renderHeader();
    expect(screen.getByText('+150.50')).toBeInTheDocument();
  });
});
