import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import OverviewPage from '../../pages/OverviewPage';
import { useTradingStore } from '../../store/tradingStore';
import { useSystemStore } from '../../store/systemStore';

const overviewData = {
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

// Capture the onMessage callback so we can simulate WS messages
let capturedOnMessage: ((msg: any) => void) | null = null;

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn((path: string, onMessage: (msg: any) => void) => {
    capturedOnMessage = onMessage;
    return { connected: true };
  }),
}));

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn(() => Promise.resolve({
    database: { name: 'postgres', status: 'connected' },
    redis: { name: 'redis', status: 'connected' },
    services: [],
  })),
}));

describe('OverviewPage', () => {
  beforeEach(() => {
    capturedOnMessage = null;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useTradingStore.setState({
      overview: null,
      signals: [],
      positions: [],
      regime: null,
      wsConnected: false,
    });
    useSystemStore.setState({
      status: null,
      services: [],
      wsConnected: false,
    });
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    );

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('System Overview')).toBeInTheDocument();
  });

  it('shows skeleton cards when loading', () => {
    const { container } = renderPage();
    expect(container.querySelectorAll('.skeleton').length).toBeGreaterThan(0);
  });

  it('renders KPI cards after WS message arrives', async () => {
    renderPage();
    // Simulate WebSocket message that triggers loading=false
    capturedOnMessage?.({ type: 'overview', data: overviewData });
    await waitFor(() => {
      expect(screen.getByText('Daily P&L')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Win Rate').length).toBeGreaterThan(0);
    expect(screen.getByText('Signals Today')).toBeInTheDocument();
    expect(screen.getByText('Open Positions')).toBeInTheDocument();
  });

  it('shows no signals message when empty', () => {
    renderPage();
    expect(screen.getByText(/No signals yet/)).toBeInTheDocument();
  });

  it('renders Grafana link', () => {
    renderPage();
    expect(screen.getByText('Grafana')).toBeInTheDocument();
  });
});
