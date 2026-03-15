import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import RiskPage from '../../pages/RiskPage';
import { useUIStore } from '../../store/uiStore';

const mockRiskData = {
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

// Mock fetchApi
vi.mock('../../api/client', () => ({
  fetchApi: vi.fn(() => Promise.resolve(mockRiskData)),
}));

describe('RiskPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({
      toasts: [],
      notifications: [],
      unreadCount: 0,
    });
  });

  const renderPage = () =>
    render(
      <MemoryRouter>
        <RiskPage />
      </MemoryRouter>
    );

  it('renders risk page title', () => {
    renderPage();
    expect(screen.getByText('Risk Management')).toBeInTheDocument();
  });

  it('renders risk metrics after data loads', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Open Positions')).toBeInTheDocument();
    });
    expect(screen.getByText('Market Regime')).toBeInTheDocument();
  });

  it('renders symbols exposed', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument();
    });
    expect(screen.getByText('GBPUSD')).toBeInTheDocument();
  });

  it('shows gauges for daily loss and drawdown', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Daily Loss')).toBeInTheDocument();
    });
    expect(screen.getByText('Drawdown')).toBeInTheDocument();
  });
});
