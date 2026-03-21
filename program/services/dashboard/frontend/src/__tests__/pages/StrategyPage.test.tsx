import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import StrategyPage from '../../pages/StrategyPage';

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

  it('displays strategy win rate', async () => {
    render(<MemoryRouter><StrategyPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('60.0%')).toBeInTheDocument();
    });
  });

  it('displays strategy profit', async () => {
    render(<MemoryRouter><StrategyPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('500.00')).toBeInTheDocument();
    });
  });
});
