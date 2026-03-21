import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ToastItem, ToastContainer } from '../../components/common/Toast';
import { useUIStore } from '../../store/uiStore';
import type { Toast } from '../../store/uiStore';

describe('ToastItem', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ toasts: [] });
  });

  const toast: Toast = {
    id: 'test-1',
    type: 'success',
    title: 'Saved',
    message: 'Your changes were saved',
  };

  it('renders title and message', () => {
    render(<ToastItem toast={toast} />);
    expect(screen.getByText('Saved')).toBeInTheDocument();
    expect(screen.getByText('Your changes were saved')).toBeInTheDocument();
  });

  it('renders dismiss button', () => {
    render(<ToastItem toast={toast} />);
    expect(screen.getByLabelText('Dismiss notification')).toBeInTheDocument();
  });

  it('close button removes toast from store', async () => {
    const user = userEvent.setup();
    // Pre-populate the store with the toast
    useUIStore.setState({ toasts: [toast] });

    render(<ToastItem toast={toast} />);
    await user.click(screen.getByLabelText('Dismiss notification'));

    // The toast should be removed from the store
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('renders without message', () => {
    const noMsg: Toast = { id: 'x', type: 'info', title: 'Info' };
    render(<ToastItem toast={noMsg} />);
    expect(screen.getByText('Info')).toBeInTheDocument();
  });

  it('renders success toast type with role=alert', () => {
    const t: Toast = { id: 't-success', type: 'success', title: 'Success toast' };
    render(<ToastItem toast={t} />);
    expect(screen.getByText('Success toast')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders error toast type', () => {
    const t: Toast = { id: 't-error', type: 'error', title: 'Error toast' };
    render(<ToastItem toast={t} />);
    expect(screen.getByText('Error toast')).toBeInTheDocument();
  });

  it('renders warning toast type', () => {
    const t: Toast = { id: 't-warning', type: 'warning', title: 'Warning toast' };
    render(<ToastItem toast={t} />);
    expect(screen.getByText('Warning toast')).toBeInTheDocument();
  });

  it('renders info toast type', () => {
    const t: Toast = { id: 't-info', type: 'info', title: 'Info toast' };
    render(<ToastItem toast={t} />);
    expect(screen.getByText('Info toast')).toBeInTheDocument();
  });
});

describe('ToastContainer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ toasts: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns null when no toasts', () => {
    const { container } = render(<ToastContainer />);
    expect(container.innerHTML).toBe('');
  });

  it('renders toasts', () => {
    useUIStore.setState({
      toasts: [
        { id: '1', type: 'success', title: 'Toast 1' },
        { id: '2', type: 'error', title: 'Toast 2' },
      ],
    });
    render(<ToastContainer />);
    expect(screen.getByText('Toast 1')).toBeInTheDocument();
    expect(screen.getByText('Toast 2')).toBeInTheDocument();
  });

  it('toast auto-dismisses after default timeout', () => {
    // addToast uses setTimeout with default 4000ms duration
    useUIStore.getState().addToast({ type: 'info', title: 'Auto dismiss me' });

    expect(useUIStore.getState().toasts).toHaveLength(1);

    // Advance past the default 4000ms timeout
    vi.advanceTimersByTime(4500);

    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('toast with custom duration auto-dismisses after that duration', () => {
    useUIStore.getState().addToast({ type: 'warning', title: 'Custom timeout', duration: 2000 });

    expect(useUIStore.getState().toasts).toHaveLength(1);

    // Should still be there before duration
    vi.advanceTimersByTime(1500);
    expect(useUIStore.getState().toasts).toHaveLength(1);

    // Should be gone after duration
    vi.advanceTimersByTime(1000);
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('toast with duration=0 does not auto-dismiss', () => {
    useUIStore.getState().addToast({ type: 'error', title: 'Persistent', duration: 0 });

    expect(useUIStore.getState().toasts).toHaveLength(1);

    // Advance a long time - it should still be there
    vi.advanceTimersByTime(60000);
    expect(useUIStore.getState().toasts).toHaveLength(1);
  });

  it('renders the notifications region with role', () => {
    useUIStore.setState({
      toasts: [{ id: '1', type: 'info', title: 'Test' }],
    });
    render(<ToastContainer />);
    expect(screen.getByRole('region', { name: 'Notifications' })).toBeInTheDocument();
  });
});
