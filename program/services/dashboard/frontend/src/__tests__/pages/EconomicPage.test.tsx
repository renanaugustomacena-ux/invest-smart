import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import EconomicPage from '../../pages/EconomicPage';

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn((path: string) => {
    if (path.includes('upcoming')) {
      return Promise.resolve({
        events: [
          { event_time: '2024-01-15T14:30:00Z', event_name: 'CPI Release', currency: 'USD', impact: 'high' },
        ],
      });
    }
    if (path.includes('blackouts')) {
      return Promise.resolve({
        blackouts: [
          { symbol: 'EURUSD', reason: 'ECB meeting', blackout_end: '2024-01-15T15:00:00Z' },
        ],
      });
    }
    return Promise.resolve({});
  }),
}));

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
});
