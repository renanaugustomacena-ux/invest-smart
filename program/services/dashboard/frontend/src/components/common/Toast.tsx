import { X, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';
import type { Toast as ToastData } from '../../store/uiStore';
import { useUIStore } from '../../store/uiStore';

const CONFIG = {
  success: { icon: CheckCircle, color: 'var(--color-accent-green)', border: '#10b981' },
  error:   { icon: XCircle,     color: 'var(--color-accent-red)',   border: '#ef4444' },
  warning: { icon: AlertTriangle, color: 'var(--color-accent-yellow)', border: '#f59e0b' },
  info:    { icon: Info,        color: 'var(--color-accent-blue)',  border: '#3b82f6' },
};

export function ToastItem({ toast }: { toast: ToastData }) {
  const removeToast = useUIStore((s) => s.removeToast);
  const { icon: Icon, color, border } = CONFIG[toast.type];

  return (
    <div
      className="animate-slide-in flex items-start gap-3 p-4 rounded-xl shadow-2xl"
      style={{
        background: 'var(--color-bg-card)',
        border: `1px solid ${border}40`,
        borderLeft: `3px solid ${border}`,
        backdropFilter: 'blur(12px)',
      }}
      role="alert"
    >
      <Icon size={18} style={{ color, flexShrink: 0, marginTop: 1 }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5 leading-relaxed">
            {toast.message}
          </p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-label="Notifications">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}
