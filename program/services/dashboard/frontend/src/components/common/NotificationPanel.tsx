import { useRef, useState, useEffect } from 'react';
import { Bell, CheckCheck, Trash2 } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';

const TYPE_COLOR: Record<string, string> = {
  success: 'var(--color-accent-green)',
  error:   'var(--color-accent-red)',
  warning: 'var(--color-accent-yellow)',
  info:    'var(--color-accent-blue)',
};

export default function NotificationPanel() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markAllRead, clearNotifications } = useUIStore();
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => { setOpen((p) => !p); if (!open) markAllRead(); }}
        className="relative p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-card)] transition-colors"
        aria-label={`Notifications (${unreadCount} unread)`}
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-0.5 flex items-center justify-center text-[10px] font-bold rounded-full bg-[var(--color-accent-red)] text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-10 w-80 glass-card shadow-2xl z-50 overflow-hidden animate-scale-in">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
            <span className="text-sm font-medium">Notifications</span>
            <div className="flex gap-1">
              <button
                onClick={markAllRead}
                className="p-1.5 rounded hover:bg-[var(--color-bg-card-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                title="Mark all read"
              >
                <CheckCheck size={14} />
              </button>
              <button
                onClick={clearNotifications}
                className="p-1.5 rounded hover:bg-[var(--color-bg-card-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                title="Clear all"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-[var(--color-text-muted)]">
                No notifications
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b border-[var(--color-border)]/50 ${!n.read ? 'bg-[var(--color-bg-card-hover)]/50' : ''}`}
                >
                  <div className="flex items-start gap-2">
                    <span
                      className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                      style={{ background: TYPE_COLOR[n.type] ?? 'var(--color-text-muted)' }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[var(--color-text-primary)]">{n.title}</p>
                      {n.message && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{n.message}</p>}
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-1">
                        {new Date(n.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
