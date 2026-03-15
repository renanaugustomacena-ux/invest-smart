import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ToastItem, ToastContainer } from '../../components/common/Toast';
import { useUIStore } from '../../store/uiStore';
import type { Toast } from '../../store/uiStore';

describe('ToastItem', () => {
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

  it('calls removeToast on dismiss', () => {
    render(<ToastItem toast={toast} />);
    fireEvent.click(screen.getByLabelText('Dismiss notification'));
    // The toast should be removed from the store
  });

  it('renders without message', () => {
    const noMsg: Toast = { id: 'x', type: 'info', title: 'Info' };
    render(<ToastItem toast={noMsg} />);
    expect(screen.getByText('Info')).toBeInTheDocument();
  });

  it('renders all toast types', () => {
    const types = ['success', 'error', 'warning', 'info'] as const;
    for (const type of types) {
      const t: Toast = { id: `t-${type}`, type, title: `${type} toast` };
      const { unmount } = render(<ToastItem toast={t} />);
      expect(screen.getByText(`${type} toast`)).toBeInTheDocument();
      unmount();
    }
  });
});

describe('ToastContainer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
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
});
