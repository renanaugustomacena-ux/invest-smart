import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import LogsPage from '../../pages/LogsPage';

vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ connected: true })),
}));

describe('LogsPage', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    // jsdom doesn't implement scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('renders page title', () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    expect(screen.getByText('Live Log Feed')).toBeInTheDocument();
  });

  it('renders filter buttons', () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    expect(screen.getByText('ALL')).toBeInTheDocument();
    // INFO appears in both filter button and log entry
    expect(screen.getAllByText('INFO').length).toBeGreaterThan(0);
    expect(screen.getByText('WARN')).toBeInTheDocument();
    expect(screen.getByText('ERROR')).toBeInTheDocument();
  });

  it('renders pause button', () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    expect(screen.getByText('Pause')).toBeInTheDocument();
  });

  it('shows live status', () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    expect(screen.getByText('Live')).toBeInTheDocument();
  });
});
