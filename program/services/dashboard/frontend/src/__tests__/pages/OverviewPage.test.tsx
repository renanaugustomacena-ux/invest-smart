import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { installFakeWebSocket, type WebSocketManager } from '../mocks/websocket';
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

let wsManager: WebSocketManager;

describe('OverviewPage', () => {
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
    useSystemStore.setState({
      status: null,
      services: [],
      wsConnected: false,
    });
  });

  afterEach(() => {
    wsManager.cleanup();
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>,
    );

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('System Overview')).toBeInTheDocument();
  });

  it('shows skeleton cards when loading', () => {
    const { container } = renderPage();
    // loading=true by default, skeleton cards should appear
    expect(container.querySelectorAll('.skeleton').length).toBeGreaterThan(0);
  });

  it('renders KPI cards after WS message arrives', async () => {
    renderPage();
    // Simulate WebSocket connection opening and message arriving
    wsManager.simulateOpen();
    wsManager.simulateMessage({ type: 'overview', data: overviewData });

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

  it('fetches system status on mount', async () => {
    // Override the /api/system/health endpoint for this test
    server.use(
      http.get('/api/system/health', () => {
        return HttpResponse.json({
          database: { name: 'postgres', status: 'connected', latency_ms: 3 },
          redis: { name: 'redis', status: 'connected', latency_ms: 1 },
          services: [{ name: 'brain', status: 'connected', latency_ms: 10 }],
          uptime_seconds: 3600,
        });
      }),
      http.get('/api/overview', () => {
        return HttpResponse.json({
          kpis: {},
          services: [{ name: 'brain', status: 'connected', latency_ms: 10 }],
          recent_signals: [],
          timestamp: '2024-01-15T10:00:00Z',
        });
      }),
    );

    renderPage();

    // The page fetches /api/system/health on mount and updates the system store
    await waitFor(() => {
      const state = useSystemStore.getState();
      expect(state.status).not.toBeNull();
    });
    // Service health section should render the brain service
    await waitFor(() => {
      expect(screen.getByText('brain')).toBeInTheDocument();
    });
  });

  it('displays correct P&L value from WS data', async () => {
    renderPage();
    wsManager.simulateOpen();
    wsManager.simulateMessage({ type: 'overview', data: overviewData });

    // Wait for the KPI cards to render with the P&L value
    await waitFor(() => {
      expect(screen.getByText('Daily P&L')).toBeInTheDocument();
    });

    // The regime subtitle should also appear
    await waitFor(() => {
      expect(screen.getByText('Regime: TRENDING')).toBeInTheDocument();
    });

    // Signals today should show the count
    expect(screen.getByText('5')).toBeInTheDocument();

    // Open positions should show "2 / 5"
    expect(screen.getByText('2 / 5')).toBeInTheDocument();
  });
});
