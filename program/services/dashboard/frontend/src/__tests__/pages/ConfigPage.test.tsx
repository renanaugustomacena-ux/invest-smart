import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import ConfigPage from '../../pages/ConfigPage';

vi.mock('../../api/client', () => ({
  fetchApi: vi.fn(() => Promise.resolve({
    database: { name: 'postgres', status: 'connected', latency_ms: 5 },
    redis: { name: 'redis', status: 'connected', latency_ms: 2 },
    services: [{ name: 'brain', status: 'connected', latency_ms: 15 }],
    uptime_seconds: 7200,
  })),
}));

describe('ConfigPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('renders page title', () => {
    render(<MemoryRouter><ConfigPage /></MemoryRouter>);
    expect(screen.getByText('System Configuration')).toBeInTheDocument();
  });

  it('shows config sections after data loads', async () => {
    render(<MemoryRouter><ConfigPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Database')).toBeInTheDocument();
    });
    expect(screen.getByText('Redis')).toBeInTheDocument();
    expect(screen.getByText('Risk Limits')).toBeInTheDocument();
    expect(screen.getByText('Services')).toBeInTheDocument();
  });

  it('shows refresh button', () => {
    render(<MemoryRouter><ConfigPage /></MemoryRouter>);
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });
});
