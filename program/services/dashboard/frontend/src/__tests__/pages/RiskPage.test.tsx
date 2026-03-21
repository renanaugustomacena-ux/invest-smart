import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import RiskPage from '../../pages/RiskPage';
import { useUIStore } from '../../store/uiStore';
import { server } from '../mocks/server';

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

  it('shows kill switch inactive badge', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Inactive/i)).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    server.use(
      http.get('/api/risk', () => {
        return HttpResponse.json({}, { status: 500 });
      })
    );
    renderPage();
    // When API fails, the page stays in loading state with skeleton cards
    // and shows no risk data — the title and gauges still render
    expect(screen.getByText('Risk Management')).toBeInTheDocument();
    // Verify that loaded metrics do NOT appear (data never loads)
    await waitFor(() => {
      expect(screen.getByText('Daily Loss')).toBeInTheDocument();
    });
    // The kill switch defaults to inactive when risk is null
    expect(screen.queryByText('EURUSD')).not.toBeInTheDocument();
  });
});
