import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import LogsPage from '../../pages/LogsPage';
import { installFakeWebSocket, type WebSocketManager } from '../mocks/websocket';

describe('LogsPage', () => {
  let wsManager: WebSocketManager;

  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    // jsdom doesn't implement scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
    wsManager = installFakeWebSocket();
  });

  afterEach(() => {
    wsManager.cleanup();
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
    // Initially disconnected since WS hasn't opened yet, but after open it shows "Live"
    act(() => {
      wsManager.simulateOpen();
    });
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('displays log entry from WS message', async () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    act(() => {
      wsManager.simulateOpen();
    });
    act(() => {
      wsManager.simulateMessage({
        type: 'overview',
        data: {
          daily_pnl: '250.00',
          open_positions: 3,
          regime: 'RANGING',
        },
      });
    });
    await waitFor(() => {
      expect(screen.getByText(/KPIs updated/)).toBeInTheDocument();
    });
    expect(screen.getByText(/PnL: 250.00/)).toBeInTheDocument();
  });

  it('pause button text changes on click', () => {
    render(<MemoryRouter><LogsPage /></MemoryRouter>);
    const pauseBtn = screen.getByText('Pause');
    expect(pauseBtn).toBeInTheDocument();
    fireEvent.click(pauseBtn);
    expect(screen.getByText('Resume')).toBeInTheDocument();
  });
});
