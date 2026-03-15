import { useState } from 'react';
import { ShieldOff, Shield, AlertTriangle, X } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';

interface KillSwitchButtonProps {
  active: boolean;
  reason?: string | null;
  onToggle?: (active: boolean) => void;
  compact?: boolean;
}

export default function KillSwitchButton({
  active,
  reason,
  onToggle,
  compact = false,
}: KillSwitchButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);
  const { addToast, addNotification } = useUIStore();

  const handleToggle = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/risk/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          active: !active,
          reason: !active ? 'Manual override from dashboard' : undefined,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const nextActive = data.kill_switch_active as boolean;

      addToast({
        type: nextActive ? 'error' : 'success',
        title: nextActive ? 'Kill Switch ACTIVATED' : 'Kill Switch deactivated',
        message: nextActive ? 'Trading has been halted.' : 'Trading is now allowed.',
      });
      addNotification({
        type: nextActive ? 'error' : 'success',
        title: nextActive ? 'Kill Switch ACTIVATED' : 'Kill Switch deactivated',
        message: nextActive ? 'Manual override from dashboard' : 'Trading resumed',
      });
      onToggle?.(nextActive);
    } catch (err: unknown) {
      addToast({ type: 'error', title: 'Kill switch failed', message: err instanceof Error ? err.message : String(err) });
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  };

  if (confirming) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-xl border-2 border-[var(--color-accent-red)]/60 bg-[var(--color-accent-red)]/5 animate-scale-in">
        <AlertTriangle size={16} className="text-[var(--color-accent-red)] flex-shrink-0" />
        <span className="text-xs text-[var(--color-text-secondary)] flex-1">
          {active ? 'Resume trading?' : 'Halt all trading?'}
        </span>
        <button
          onClick={handleToggle}
          disabled={loading}
          className="px-3 py-1 rounded-lg text-xs font-semibold bg-[var(--color-accent-red)] text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading ? '…' : 'Confirm'}
        </button>
        <button
          onClick={() => setConfirming(false)}
          className="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          aria-label="Cancel"
        >
          <X size={14} />
        </button>
      </div>
    );
  }

  if (compact) {
    return (
      <button
        onClick={() => setConfirming(true)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
          active
            ? 'bg-[var(--color-accent-red)]/20 text-[var(--color-accent-red)] border border-[var(--color-accent-red)]/40 animate-pulse-glow'
            : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)] border border-[var(--color-border)] hover:border-[var(--color-accent-red)]/40 hover:text-[var(--color-accent-red)]'
        }`}
        aria-label={active ? 'Kill switch active — click to deactivate' : 'Click to activate kill switch'}
      >
        {active ? <ShieldOff size={12} /> : <Shield size={12} />}
        {active ? 'KILL SWITCH' : 'Kill Switch'}
      </button>
    );
  }

  return (
    <div className={`glass-card p-5 ${active ? 'border border-[var(--color-accent-red)]/40' : ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium text-[var(--color-text-muted)]">Kill Switch</h3>
          {reason && active && (
            <p className="text-xs text-[var(--color-accent-red)] mt-1">{reason}</p>
          )}
        </div>
        {active
          ? <ShieldOff size={28} className="text-[var(--color-accent-red)] animate-pulse-glow" />
          : <Shield size={28} className="text-[var(--color-accent-green)]" />
        }
      </div>

      <div className={`flex items-center gap-2 mb-4 px-3 py-2 rounded-lg ${
        active
          ? 'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)]'
          : 'bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]'
      }`}>
        <span className={`w-2 h-2 rounded-full ${active ? 'bg-[var(--color-accent-red)] animate-pulse-glow' : 'bg-[var(--color-accent-green)]'}`} />
        <span className="text-sm font-semibold">{active ? 'ACTIVATED — Trading Halted' : 'Inactive — Trading OK'}</span>
      </div>

      <button
        onClick={() => setConfirming(true)}
        className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
          active
            ? 'bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)] border border-[var(--color-accent-green)]/30 hover:bg-[var(--color-accent-green)]/20'
            : 'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)] border border-[var(--color-accent-red)]/30 hover:bg-[var(--color-accent-red)]/20'
        }`}
      >
        {active ? 'Deactivate Kill Switch' : 'Activate Kill Switch'}
      </button>
    </div>
  );
}
