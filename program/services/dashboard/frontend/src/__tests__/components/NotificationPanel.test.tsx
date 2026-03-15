import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import NotificationPanel from '../../components/common/NotificationPanel';
import { useUIStore } from '../../store/uiStore';

describe('NotificationPanel', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({
      notifications: [],
      unreadCount: 0,
      toasts: [],
    });
  });

  it('renders bell button', () => {
    render(<NotificationPanel />);
    expect(screen.getByLabelText('Notifications (0 unread)')).toBeInTheDocument();
  });

  it('shows unread badge', () => {
    useUIStore.setState({ unreadCount: 3 });
    render(<NotificationPanel />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows 9+ for more than 9 unread', () => {
    useUIStore.setState({ unreadCount: 15 });
    render(<NotificationPanel />);
    expect(screen.getByText('9+')).toBeInTheDocument();
  });

  it('opens panel and shows empty state', () => {
    render(<NotificationPanel />);
    fireEvent.click(screen.getByLabelText('Notifications (0 unread)'));
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('No notifications')).toBeInTheDocument();
  });

  it('shows notifications when present', () => {
    useUIStore.setState({
      notifications: [
        { id: 'n1', type: 'success', title: 'Trade executed', timestamp: Date.now(), read: false },
      ],
      unreadCount: 1,
    });
    render(<NotificationPanel />);
    fireEvent.click(screen.getByLabelText('Notifications (1 unread)'));
    expect(screen.getByText('Trade executed')).toBeInTheDocument();
  });

  it('clear all button works', () => {
    useUIStore.setState({
      notifications: [
        { id: 'n1', type: 'info', title: 'Test', timestamp: Date.now(), read: false },
      ],
      unreadCount: 1,
    });
    render(<NotificationPanel />);
    fireEvent.click(screen.getByLabelText('Notifications (1 unread)'));
    fireEvent.click(screen.getByTitle('Clear all'));
    expect(useUIStore.getState().notifications).toHaveLength(0);
  });
});
