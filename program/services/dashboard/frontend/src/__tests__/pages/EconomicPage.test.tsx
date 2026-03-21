import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import EconomicPage from '../../pages/EconomicPage';

describe('EconomicPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('renders page title', () => {
    render(<MemoryRouter><EconomicPage /></MemoryRouter>);
    expect(screen.getByText('Economic Calendar')).toBeInTheDocument();
  });

  it('shows events after load', async () => {
    render(<MemoryRouter><EconomicPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('CPI Release')).toBeInTheDocument();
    });
  });

  it('shows blackout banner', async () => {
    render(<MemoryRouter><EconomicPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Active Trading Blackouts/)).toBeInTheDocument();
    });
    expect(screen.getByText('EURUSD')).toBeInTheDocument();
  });

  it('shows impact badge', async () => {
    render(<MemoryRouter><EconomicPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('high')).toBeInTheDocument();
    });
  });

  it('shows blackout reason', async () => {
    render(<MemoryRouter><EconomicPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('ECB meeting')).toBeInTheDocument();
    });
  });
});
