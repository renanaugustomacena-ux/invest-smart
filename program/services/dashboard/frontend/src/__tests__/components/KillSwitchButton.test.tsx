import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
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

  it('renders active state (full card)', () => {
    render(<KillSwitchButton active={true} reason="Max drawdown" />);
    expect(screen.getByText('ACTIVATED — Trading Halted')).toBeInTheDocument();
    expect(screen.getByText('Max drawdown')).toBeInTheDocument();
    expect(screen.getByText('Deactivate Kill Switch')).toBeInTheDocument();
  });

  it('shows confirmation on click', () => {
    render(<KillSwitchButton active={false} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    expect(screen.getByText('Halt all trading?')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('cancels confirmation', () => {
    render(<KillSwitchButton active={false} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByLabelText('Cancel'));
    expect(screen.getByText('Activate Kill Switch')).toBeInTheDocument();
  });

  it('renders compact mode inactive', () => {
    render(<KillSwitchButton active={false} compact />);
    expect(screen.getByText('Kill Switch')).toBeInTheDocument();
  });

  it('renders compact mode active', () => {
    render(<KillSwitchButton active={true} compact />);
    expect(screen.getByText('KILL SWITCH')).toBeInTheDocument();
  });

  it('handles API success on confirm', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ kill_switch_active: true }),
    } as Response);

    const onToggle = vi.fn();
    render(<KillSwitchButton active={false} onToggle={onToggle} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByText('Confirm'));

    // Wait for async
    await vi.waitFor(() => {
      expect(onToggle).toHaveBeenCalledWith(true);
    });
  });

  it('handles API error on confirm', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);

    render(<KillSwitchButton active={false} />);
    fireEvent.click(screen.getByText('Activate Kill Switch'));
    fireEvent.click(screen.getByText('Confirm'));

    await vi.waitFor(() => {
      const toasts = useUIStore.getState().toasts;
      expect(toasts.some((t) => t.title === 'Kill switch failed')).toBe(true);
    });
  });
});
