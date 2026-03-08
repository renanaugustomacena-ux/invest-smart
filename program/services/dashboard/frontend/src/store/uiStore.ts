import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

export interface Notification {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  timestamp: number;
  read: boolean;
}

interface UIState {
  sidebarCollapsed: boolean;
  theme: 'dark' | 'light';
  toasts: Toast[];
  notifications: Notification[];
  unreadCount: number;
  paletteOpen: boolean;

  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleTheme: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  addNotification: (n: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAllRead: () => void;
  clearNotifications: () => void;
  setPaletteOpen: (open: boolean) => void;
}

const saved = {
  theme: (localStorage.getItem('moneymaker_theme') as 'dark' | 'light' | null) ?? 'dark',
  collapsed: localStorage.getItem('moneymaker_sidebar') === 'true',
};

export const useUIStore = create<UIState>((set, get) => ({
  sidebarCollapsed: saved.collapsed,
  theme: saved.theme,
  toasts: [],
  notifications: [],
  unreadCount: 0,
  paletteOpen: false,

  toggleSidebar: () => {
    const next = !get().sidebarCollapsed;
    localStorage.setItem('moneymaker_sidebar', String(next));
    set({ sidebarCollapsed: next });
  },

  setSidebarCollapsed: (collapsed) => {
    localStorage.setItem('moneymaker_sidebar', String(collapsed));
    set({ sidebarCollapsed: collapsed });
  },

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('moneymaker_theme', next);
    document.documentElement.setAttribute('data-theme', next);
    set({ theme: next });
  },

  addToast: (toast) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
    const duration = toast.duration ?? 4000;
    if (duration > 0) {
      setTimeout(() => get().removeToast(id), duration);
    }
  },

  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  addNotification: (n) => {
    const notif: Notification = {
      id: `notif_${Date.now()}_${Math.random().toString(36).slice(2)}`,
      timestamp: Date.now(),
      read: false,
      ...n,
    };
    set((s) => ({
      notifications: [notif, ...s.notifications].slice(0, 50),
      unreadCount: s.unreadCount + 1,
    }));
  },

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clearNotifications: () => set({ notifications: [], unreadCount: 0 }),

  setPaletteOpen: (open) => set({ paletteOpen: open }),
}));
