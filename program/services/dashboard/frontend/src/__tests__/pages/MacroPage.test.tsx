import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import MacroPage from '../../pages/MacroPage';

const mockSnapshot = {
  snapshot: {
    vix_spot: '18.5',
    vix_regime: 'LOW',
    yield_slope: '0.45',
    curve_inverted: false,
    dxy_value: '104.5',
    dxy_trend: '1',
    recession_prob: '12.5',
    updated_at: '2024-01-15T10:00:00Z',
  },
};

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn((path: string) => {
    if (path.includes('/api/macro/snapshot')) return Promise.resolve(mockSnapshot);
    if (path.includes('/api/macro/vix')) return Promise.resolve({ data: [] });
    if (path.includes('/api/macro/dxy')) return Promise.resolve({ data: [] });
    return Promise.resolve({});
  }),
}));

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
});
