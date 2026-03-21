import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import MacroPage from '../../pages/MacroPage';

describe('MacroPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('renders page title', () => {
    render(<MemoryRouter><MacroPage /></MemoryRouter>);
    expect(screen.getByText('Macro Indicators')).toBeInTheDocument();
  });

  it('shows KPIs after data loads', async () => {
    render(<MemoryRouter><MacroPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('VIX Spot')).toBeInTheDocument();
    });
    expect(screen.getByText(/Yield Spread/)).toBeInTheDocument();
    expect(screen.getByText(/DXY/)).toBeInTheDocument();
    expect(screen.getByText('Recession Probability')).toBeInTheDocument();
  });

  it('displays VIX regime badge', async () => {
    render(<MemoryRouter><MacroPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Low')).toBeInTheDocument();
    });
  });

  it('displays recession probability value', async () => {
    render(<MemoryRouter><MacroPage /></MemoryRouter>);
    await waitFor(() => {
      const matches = screen.getAllByText('12.5%');
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });
});
