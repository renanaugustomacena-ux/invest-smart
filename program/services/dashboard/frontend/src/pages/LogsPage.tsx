import { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, Circle, ArrowDown, Pause, Play } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';

type LogLevel = 'ALL' | 'ERROR' | 'WARN' | 'INFO';

interface LogEntry {
  id: number;
  timestamp: string;
  level: LogLevel | string;
  source: string;
  message: string;
}

const LEVEL_COLOR: Record<string, string> = {
  ERROR: 'text-[var(--color-accent-red)]',
  WARN:  'text-[var(--color-accent-yellow)]',
  INFO:  'text-[var(--color-text-secondary)]',
  ALL:   'text-[var(--color-text-muted)]',
};

const LEVEL_BG: Record<string, string> = {
  ERROR: 'bg-[var(--color-accent-red)]/5',
  WARN:  'bg-[var(--color-accent-yellow)]/5',
  INFO:  '',
};

let _idCounter = 0;

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogLevel>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((entry: Omit<LogEntry, 'id'>) => {
    if (paused) return;
    setLogs((prev) => {
      const next = [...prev, { ...entry, id: ++_idCounter }];
      return next.length > 500 ? next.slice(-500) : next;
    });
  }, [paused]);

  // Subscribe to the overview stream and translate state changes into log entries
  const onMessage = useCallback((msg: any) => {
    if (msg?.type === 'overview' && msg.data) {
      const d = msg.data;
      const ts = new Date().toISOString();
      addLog({ timestamp: ts, level: 'INFO', source: 'overview', message: `KPIs updated — PnL: ${d.daily_pnl} | Positions: ${d.open_positions} | Regime: ${d.regime ?? 'n/a'}` });
      if (d.kill_switch_active) {
        addLog({ timestamp: ts, level: 'ERROR', source: 'kill-switch', message: 'Kill switch is ACTIVE — trading halted' });
      }
    }
    if (msg?.type === 'error') {
      addLog({ timestamp: new Date().toISOString(), level: 'WARN', source: 'websocket', message: msg.data?.message ?? 'WebSocket error' });
    }
  }, [addLog]);

  const { connected } = useWebSocket('/ws/overview', onMessage);

  // Log connection events
  useEffect(() => {
    addLog({
      timestamp: new Date().toISOString(),
      level: 'INFO',
      source: 'dashboard',
      message: connected ? 'WebSocket connected to /ws/overview' : 'WebSocket disconnected — reconnecting…',
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connected]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const displayed = filter === 'ALL' ? logs : logs.filter((l) => l.level === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <FileText size={22} />
          Live Log Feed
        </h1>

        {/* Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Level filter */}
          {(['ALL', 'INFO', 'WARN', 'ERROR'] as const).map((l) => (
            <button
              key={l}
              onClick={() => setFilter(l)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                filter === l
                  ? 'bg-[var(--color-accent-blue)] text-white'
                  : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)]'
              }`}
            >
              {l}
            </button>
          ))}

          <div className="w-px h-5 bg-[var(--color-border)]" />

          {/* Auto-scroll */}
          <button
            onClick={() => setAutoScroll((p) => !p)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-colors border ${
              autoScroll
                ? 'bg-[var(--color-accent-blue)]/10 text-[var(--color-accent-blue)] border-[var(--color-accent-blue)]/30'
                : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)] border-[var(--color-border)]'
            }`}
            title="Toggle auto-scroll"
          >
            <ArrowDown size={12} /> Scroll
          </button>

          {/* Pause */}
          <button
            onClick={() => setPaused((p) => !p)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-colors border ${
              paused
                ? 'bg-[var(--color-accent-yellow)]/10 text-[var(--color-accent-yellow)] border-[var(--color-accent-yellow)]/30'
                : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)] border-[var(--color-border)]'
            }`}
          >
            {paused ? <Play size={12} /> : <Pause size={12} />}
            {paused ? 'Resume' : 'Pause'}
          </button>

          {/* WS status */}
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
            <Circle
              size={8}
              fill={connected ? 'var(--color-accent-green)' : 'var(--color-accent-red)'}
              stroke="none"
            />
            {connected ? 'Live' : 'Offline'}
          </div>
        </div>
      </div>

      {/* Log area */}
      <div
        ref={containerRef}
        className="glass-card overflow-auto font-mono text-xs"
        style={{ height: 'calc(100vh - 220px)', minHeight: 400 }}
      >
        {displayed.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
            Waiting for log events…
          </div>
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 bg-[var(--color-bg-secondary)] z-10">
              <tr>
                <th className="px-4 py-2 text-left text-[var(--color-text-muted)] font-normal w-48">Time</th>
                <th className="px-2 py-2 text-left text-[var(--color-text-muted)] font-normal w-16">Level</th>
                <th className="px-2 py-2 text-left text-[var(--color-text-muted)] font-normal w-28">Source</th>
                <th className="px-2 py-2 text-left text-[var(--color-text-muted)] font-normal">Message</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((log) => (
                <tr
                  key={log.id}
                  className={`border-t border-[var(--color-border)]/30 hover:bg-[var(--color-bg-card-hover)]/50 ${LEVEL_BG[log.level] ?? ''}`}
                >
                  <td className="px-4 py-1.5 text-[var(--color-text-muted)] whitespace-nowrap">
                    {log.timestamp.slice(11, 23)}
                  </td>
                  <td className={`px-2 py-1.5 font-semibold whitespace-nowrap ${LEVEL_COLOR[log.level] ?? 'text-[var(--color-text-muted)]'}`}>
                    {log.level}
                  </td>
                  <td className="px-2 py-1.5 text-[var(--color-accent-blue)] whitespace-nowrap">
                    {log.source}
                  </td>
                  <td className="px-2 py-1.5 text-[var(--color-text-primary)] break-all">
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div ref={bottomRef} />
      </div>

      <p className="text-xs text-[var(--color-text-muted)]">
        Showing {displayed.length} entries (max 500) — full audit trail: query the <code className="bg-[var(--color-bg-card)] px-1 rounded">audit_log</code> table in TimescaleDB
      </p>
    </div>
  );
}
