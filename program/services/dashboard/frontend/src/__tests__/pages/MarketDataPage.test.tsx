import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import MarketDataPage from '../../pages/MarketDataPage';

// Mock lightweight-charts createChart
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  })),
  CandlestickSeries: {},
}));

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn((path: string) => {
    if (path.includes('symbols')) return Promise.resolve({ symbols: ['EURUSD', 'GBPUSD'] });
    if (path.includes('bars')) return Promise.resolve({ bars: [] });
    return Promise.resolve({});
  }),
}));

describe('MarketDataPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('renders page title', () => {
    render(<MemoryRouter><MarketDataPage /></MemoryRouter>);
    expect(screen.getByText('Market Data')).toBeInTheDocument();
  });

  it('renders timeframe buttons', () => {
    render(<MemoryRouter><MarketDataPage /></MemoryRouter>);
    expect(screen.getByText('M5')).toBeInTheDocument();
    expect(screen.getByText('H1')).toBeInTheDocument();
    expect(screen.getByText('D1')).toBeInTheDocument();
  });
});
