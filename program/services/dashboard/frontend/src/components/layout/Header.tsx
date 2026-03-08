import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import ThemeToggle from '../common/ThemeToggle';
import NotificationPanel from '../common/NotificationPanel';
import { useTradingStore } from '../../store/tradingStore';

function LiveClock() {
  const [time, setTime] = useState(() => new Date().toUTCString().slice(17, 25));
  useEffect(() => {
    const id = setInterval(() => setTime(new Date().toUTCString().slice(17, 25)), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="text-xs font-mono text-[var(--color-text-muted)]">
      {time} UTC
    </span>
  );
}

function WsPill({ connected }: { connected: boolean }) {
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
      connected
        ? 'bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)] border-[var(--color-accent-green)]/20'
        : 'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)] border-[var(--color-accent-red)]/20'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-[var(--color-accent-green)] animate-pulse-glow' : 'bg-[var(--color-accent-red)]'}`} />
      {connected ? 'Live' : 'Reconnecting…'}
    </div>
  );
}

export default function Header({ wsConnected }: { wsConnected?: boolean }) {
  const overview = useTradingStore((s) => s.overview);
  const pnl = overview ? parseFloat(overview.daily_pnl) : null;
  const pnlPositive = pnl !== null && pnl >= 0;

  return (
    <header className="h-14 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Left: branding */}
      <div className="flex items-center gap-2">
        <Activity size={16} className="text-[var(--color-accent-blue)]" />
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">MONEYMAKER</span>
        <span className="text-xs text-[var(--color-text-muted)] hidden sm:block">V1</span>
      </div>

      {/* Center: live clock */}
      <div className="hidden md:flex items-center">
        <LiveClock />
      </div>

      {/* Right: quick metrics + controls */}
      <div className="flex items-center gap-3">
        {/* Daily PnL */}
        {pnl !== null && (
          <span className={`text-xs font-semibold hidden lg:block ${pnlPositive ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}`}>
            {pnlPositive ? '+' : ''}{pnl.toFixed(2)}
          </span>
        )}

        {/* WS status */}
        <WsPill connected={wsConnected ?? false} />

        {/* Notifications */}
        <NotificationPanel />

        {/* Theme */}
        <ThemeToggle />

        {/* Ctrl+K hint */}
        <kbd className="hidden sm:flex items-center gap-1 px-2 py-1 text-[10px] rounded bg-[var(--color-bg-card)] border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-default">
          <span>⌘</span><span>K</span>
        </kbd>

        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-[var(--color-accent-blue)] flex items-center justify-center text-xs font-bold text-white">
          G
        </div>
      </div>
    </header>
  );
}
