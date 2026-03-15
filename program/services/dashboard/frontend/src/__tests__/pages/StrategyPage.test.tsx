import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import StrategyPage from '../../pages/StrategyPage';

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn(() => Promise.resolve({
    data: [
      {
        strategy_name: 'coper',
        symbol: 'EURUSD',
        total_signals: 50,
        wins: 30,
        losses: 20,
        total_profit: '500.00',
        avg_confidence: '0.72',
        win_rate: '60.0',
      },
    ],
  })),
}));

describe('StrategyPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('renders page title', () => {
    render(<MemoryRouter><StrategyPage /></MemoryRouter>);
    expect(screen.getByText('Strategy Performance')).toBeInTheDocument();
  });

  it('shows strategy data after load', async () => {
    render(<MemoryRouter><StrategyPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('coper')).toBeInTheDocument();
    });
    expect(screen.getByText('EURUSD')).toBeInTheDocument();
  });
});
