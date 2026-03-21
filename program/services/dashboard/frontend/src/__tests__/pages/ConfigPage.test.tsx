import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import ConfigPage from '../../pages/ConfigPage';

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

  it('shows uptime', async () => {
    render(<MemoryRouter><ConfigPage /></MemoryRouter>);
    // defaultSystemStatus has uptime_seconds: 7200 => "2h 0m"
    await waitFor(() => {
      expect(screen.getByText(/Uptime: 2h 0m/)).toBeInTheDocument();
    });
  });

  it('refresh button triggers new fetch', async () => {
    render(<MemoryRouter><ConfigPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Database')).toBeInTheDocument();
    });
    const refreshBtn = screen.getByText('Refresh');
    fireEvent.click(refreshBtn);
    // After refresh, data should still be displayed (MSW returns same data)
    await waitFor(() => {
      expect(screen.getByText('Database')).toBeInTheDocument();
    });
    expect(screen.getByText('Redis')).toBeInTheDocument();
  });
});
