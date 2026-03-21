import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import KillSwitchButton from '../../components/common/KillSwitchButton';
import { useUIStore } from '../../store/uiStore';

describe('KillSwitchButton', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ toasts: [], notifications: [], unreadCount: 0 });
  });

  it('renders inactive state (full card)', () => {
    render(<KillSwitchButton active={false} />);
    expect(screen.getByText('Kill Switch')).toBeInTheDocument();
    expect(screen.getByText('Inactive — Trading OK')).toBeInTheDocument();
    expect(screen.getByText('Activate Kill Switch')).toBeInTheDocument();
  });

  it('renders active state with correct text', () => {
    render(<KillSwitchButton active={true} reason="Max drawdown" />);
    expect(screen.getByText('ACTIVATED — Trading Halted')).toBeInTheDocument();
    expect(screen.getByText('Max drawdown')).toBeInTheDocument();
    expect(screen.getByText('Deactivate Kill Switch')).toBeInTheDocument();
  });

  it('click Activate shows confirmation dialog', async () => {
    const user = userEvent.setup();
    render(<KillSwitchButton active={false} />);
    await user.click(screen.getByText('Activate Kill Switch'));
    expect(screen.getByText('Halt all trading?')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('click Cancel dismisses dialog', async () => {
    const user = userEvent.setup();
    render(<KillSwitchButton active={false} />);
    await user.click(screen.getByText('Activate Kill Switch'));
    expect(screen.getByText('Halt all trading?')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Cancel'));
    expect(screen.getByText('Activate Kill Switch')).toBeInTheDocument();
    expect(screen.queryByText('Halt all trading?')).not.toBeInTheDocument();
  });

  it('double-click protection: button disabled during API call', async () => {
    // Use a delayed MSW handler so we can observe the loading state
    let resolveResponse!: () => void;
    const responsePromise = new Promise<void>((resolve) => {
      resolveResponse = resolve;
    });

    server.use(
      http.post('/api/risk/kill-switch', async () => {
        await responsePromise;
        return HttpResponse.json({ kill_switch_active: true });
      })
    );

    render(<KillSwitchButton active={false} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByText('Confirm'));

    // While the request is in-flight, the Confirm button shows "..." and is disabled
    await waitFor(() => {
      const loadingIndicator = screen.getByText('…');
      expect(loadingIndicator).toBeInTheDocument();
      expect(loadingIndicator.closest('button')).toBeDisabled();
    });

    // Resolve the request to clean up
    resolveResponse();
    await waitFor(() => {
      expect(screen.queryByText('…')).not.toBeInTheDocument();
    });
  });

  it('renders compact mode inactive', () => {
    render(<KillSwitchButton active={false} compact />);
    expect(screen.getByText('Kill Switch')).toBeInTheDocument();
  });

  it('renders compact mode active', () => {
    render(<KillSwitchButton active={true} compact />);
    expect(screen.getByText('KILL SWITCH')).toBeInTheDocument();
  });

  it('handles API success on confirm (MSW)', async () => {
    server.use(
      http.post('/api/risk/kill-switch', () => {
        return HttpResponse.json({ kill_switch_active: true });
      })
    );

    const onToggle = vi.fn();
    render(<KillSwitchButton active={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(onToggle).toHaveBeenCalledWith(true);
    });

    // Verify success toast was added
    const toasts = useUIStore.getState().toasts;
    expect(toasts.some((t) => t.title === 'Kill Switch ACTIVATED')).toBe(true);
  });

  it('handles API error on confirm (MSW)', async () => {
    server.use(
      http.post('/api/risk/kill-switch', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(<KillSwitchButton active={false} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      const toasts = useUIStore.getState().toasts;
      expect(toasts.some((t) => t.title === 'Kill switch failed')).toBe(true);
    });
  });

  it('handles deactivation flow when active', async () => {
    server.use(
      http.post('/api/risk/kill-switch', () => {
        return HttpResponse.json({ kill_switch_active: false });
      })
    );

    const onToggle = vi.fn();
    render(<KillSwitchButton active={true} onToggle={onToggle} />);
    fireEvent.click(screen.getByText('Deactivate Kill Switch'));
    expect(screen.getByText('Resume trading?')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(onToggle).toHaveBeenCalledWith(false);
    });

    const toasts = useUIStore.getState().toasts;
    expect(toasts.some((t) => t.title === 'Kill Switch deactivated')).toBe(true);
  });
});
