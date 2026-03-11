import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, LayoutDashboard, TrendingUp, ShieldAlert, BarChart3,
  Globe, Target, CalendarDays, FileText, Settings, Sun, Moon,
} from 'lucide-react';
import { useUIStore } from '../../store/uiStore';

interface PaletteItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ElementType;
  action: () => void;
}

export default function CommandPalette() {
  const { paletteOpen, setPaletteOpen, toggleTheme, theme } = useUIStore();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const nav = (path: string) => { navigate(path); setPaletteOpen(false); };

  const items: PaletteItem[] = [
    { id: 'overview',  label: 'Overview',           description: 'System KPIs & services',  icon: LayoutDashboard, action: () => nav('/') },
    { id: 'trading',   label: 'Trading',             description: 'Signals & executions',    icon: TrendingUp,       action: () => nav('/trading') },
    { id: 'risk',      label: 'Risk',                description: 'Drawdown & kill switch',  icon: ShieldAlert,      action: () => nav('/risk') },
    { id: 'market',    label: 'Market Data',         description: 'OHLCV candlestick chart', icon: BarChart3,        action: () => nav('/market') },
    { id: 'macro',     label: 'Macro',               description: 'VIX, yield curve, DXY',   icon: Globe,            action: () => nav('/macro') },
    { id: 'strategy',  label: 'Strategy',            description: 'Performance attribution', icon: Target,           action: () => nav('/strategy') },
    { id: 'economic',  label: 'Economic Calendar',   description: 'Events & blackouts',      icon: CalendarDays,     action: () => nav('/economic') },
    { id: 'logs',      label: 'Logs',                description: 'Audit trail',             icon: FileText,         action: () => nav('/logs') },
    { id: 'config',    label: 'Config',              description: 'System configuration',   icon: Settings,         action: () => nav('/config') },
    {
      id: 'theme',
      label: `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`,
      icon: theme === 'dark' ? Sun : Moon,
      action: () => { toggleTheme(); setPaletteOpen(false); },
    },
  ];

  const filtered = query.trim()
    ? items.filter((i) =>
        `${i.label} ${i.description ?? ''}`.toLowerCase().includes(query.toLowerCase())
      )
    : items;

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen(!paletteOpen);
      }
      if (e.key === 'Escape') setPaletteOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [paletteOpen, setPaletteOpen]);

  // Focus input when opened
  useEffect(() => {
    if (paletteOpen) {
      setQuery('');
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [paletteOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected((s) => Math.min(s + 1, filtered.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setSelected((s) => Math.max(s - 1, 0)); }
    if (e.key === 'Enter' && filtered[selected]) { filtered[selected].action(); }
  };

  if (!paletteOpen) return null;

  return (
    <div className="palette-backdrop" onClick={() => setPaletteOpen(false)}>
      <div
        className="fixed left-1/2 top-1/4 -translate-x-1/2 w-full max-w-lg z-110 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="glass-card overflow-hidden shadow-2xl">
          {/* Search bar */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)]">
            <Search size={16} className="text-[var(--color-text-muted)] flex-shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
              onKeyDown={handleKeyDown}
              placeholder="Search pages or actions…"
              className="flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none"
            />
            <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] border border-[var(--color-border)]">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto py-2">
            {filtered.length === 0 ? (
              <p className="px-4 py-3 text-sm text-[var(--color-text-muted)]">No results</p>
            ) : (
              filtered.map((item, i) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={item.action}
                    onMouseEnter={() => setSelected(i)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                      selected === i
                        ? 'bg-[var(--color-accent-blue)]/10 text-[var(--color-accent-blue)]'
                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card-hover)]'
                    }`}
                  >
                    <Icon size={16} className="flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{item.label}</p>
                      {item.description && (
                        <p className="text-xs text-[var(--color-text-muted)]">{item.description}</p>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="px-4 py-2 border-t border-[var(--color-border)] flex gap-3 text-[10px] text-[var(--color-text-muted)]">
            <span><kbd className="font-mono">↑↓</kbd> navigate</span>
            <span><kbd className="font-mono">↵</kbd> select</span>
            <span><kbd className="font-mono">Ctrl+K</kbd> toggle</span>
          </div>
        </div>
      </div>
    </div>
  );
}
