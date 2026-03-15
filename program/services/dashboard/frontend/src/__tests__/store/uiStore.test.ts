import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useUIStore } from '../../store/uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store state
    useUIStore.setState({
      sidebarCollapsed: false,
      theme: 'dark',
      toasts: [],
      notifications: [],
      unreadCount: 0,
      paletteOpen: false,
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  it('toggleSidebar flips collapsed state', () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  it('setSidebarCollapsed sets explicit value', () => {
    useUIStore.getState().setSidebarCollapsed(true);
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });

  it('toggleTheme switches between dark and light', () => {
    expect(useUIStore.getState().theme).toBe('dark');
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().theme).toBe('light');
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().theme).toBe('dark');
  });

  it('addToast adds a toast and auto-generates id', () => {
    vi.useFakeTimers();
    useUIStore.getState().addToast({ type: 'success', title: 'Done' });
    const toasts = useUIStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].title).toBe('Done');
    expect(toasts[0].type).toBe('success');
    expect(toasts[0].id).toMatch(/^toast_/);
    vi.useRealTimers();
  });

  it('removeToast removes by id', () => {
    vi.useFakeTimers();
    useUIStore.getState().addToast({ type: 'info', title: 'Test', duration: 0 });
    const id = useUIStore.getState().toasts[0].id;
    useUIStore.getState().removeToast(id);
    expect(useUIStore.getState().toasts).toHaveLength(0);
    vi.useRealTimers();
  });

  it('addNotification adds to front and increments unread', () => {
    useUIStore.getState().addNotification({ type: 'error', title: 'Alert' });
    const state = useUIStore.getState();
    expect(state.notifications).toHaveLength(1);
    expect(state.notifications[0].title).toBe('Alert');
    expect(state.notifications[0].read).toBe(false);
    expect(state.unreadCount).toBe(1);
  });

  it('addNotification caps at 50', () => {
    for (let i = 0; i < 55; i++) {
      useUIStore.getState().addNotification({ type: 'info', title: `N${i}` });
    }
    expect(useUIStore.getState().notifications).toHaveLength(50);
  });

  it('markAllRead sets all to read and resets count', () => {
    useUIStore.getState().addNotification({ type: 'info', title: 'A' });
    useUIStore.getState().addNotification({ type: 'info', title: 'B' });
    expect(useUIStore.getState().unreadCount).toBe(2);

    useUIStore.getState().markAllRead();
    const state = useUIStore.getState();
    expect(state.unreadCount).toBe(0);
    expect(state.notifications.every((n) => n.read)).toBe(true);
  });

  it('clearNotifications empties list and resets count', () => {
    useUIStore.getState().addNotification({ type: 'info', title: 'X' });
    useUIStore.getState().clearNotifications();
    expect(useUIStore.getState().notifications).toHaveLength(0);
    expect(useUIStore.getState().unreadCount).toBe(0);
  });

  it('setPaletteOpen toggles palette state', () => {
    useUIStore.getState().setPaletteOpen(true);
    expect(useUIStore.getState().paletteOpen).toBe(true);
    useUIStore.getState().setPaletteOpen(false);
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });
});
