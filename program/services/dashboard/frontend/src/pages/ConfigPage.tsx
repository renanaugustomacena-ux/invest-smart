import { useEffect, useState } from 'react';
import { Settings, Database, Activity, Shield, Brain, RefreshCw } from 'lucide-react';
import StatusBadge from '../components/common/StatusBadge';
import { fetchApi } from '../api/client';
import type { SystemStatus } from '../api/types';

interface ConfigSection {
  title: string;
  icon: React.ElementType;
  items: { label: string; value: string; mono?: boolean }[];
}

export default function ConfigPage() {
  const [health, setHealth] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = async () => {
    try {
      const data = await fetchApi<SystemStatus>('/api/system/health');
      setHealth(data);
      setLoading(false);
      setLastRefresh(new Date());
    } catch { /* ignore */ }
  };

  useEffect(() => {
    load();
  }, []);

  const sections: ConfigSection[] = [
    {
      title: 'Database',
      icon: Database,
      items: [
        { label: 'Status', value: health?.database?.status ?? '-' },
        { label: 'Latency', value: health?.database?.latency_ms != null ? `${Math.round(health.database.latency_ms)}ms` : '-' },
        { label: 'Engine', value: 'TimescaleDB / PostgreSQL 15' },
        { label: 'Port', value: '5432', mono: true },
      ],
    },
    {
      title: 'Redis',
      icon: Activity,
      items: [
        { label: 'Status', value: health?.redis?.status ?? '-' },
        { label: 'Latency', value: health?.redis?.latency_ms != null ? `${Math.round(health.redis.latency_ms)}ms` : '-' },
        { label: 'Port', value: '6379', mono: true },
        { label: 'Use', value: 'Brain state, kill-switch, portfolio cache' },
      ],
    },
    {
      title: 'Risk Limits',
      icon: Shield,
      items: [
        { label: 'Daily Loss Limit',  value: '2.0%' },
        { label: 'Drawdown Limit',    value: '5.0%' },
        { label: 'Max Positions',     value: '5' },
        { label: 'Spiral Threshold',  value: '3 consecutive losses' },
      ],
    },
    {
      title: 'Services',
      icon: Brain,
      items: [
        { label: 'Algo Engine gRPC',    value: ':50054', mono: true },
        { label: 'MT5 Bridge gRPC',  value: ':50055', mono: true },
        { label: 'Data Ingestion',   value: ':8081 (health) · :5555 (ZMQ)', mono: true },
        { label: 'Dashboard API',    value: ':8888', mono: true },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <Settings size={22} />
          System Configuration
        </h1>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[var(--color-bg-card)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="glass-card p-4 flex items-center gap-3 text-sm">
        <Shield size={14} className="text-[var(--color-accent-blue)] flex-shrink-0" />
        <p className="text-[var(--color-text-secondary)]">
          Configuration is managed via environment variables and <code className="bg-[var(--color-bg-secondary)] px-1 rounded text-xs">.env</code> files.
          This view shows the live runtime state — no values are editable from the dashboard for security reasons.
        </p>
      </div>

      {/* Service health strip */}
      {health?.services && health.services.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
            <Activity size={14} /> Live Service Health
          </h3>
          <div className="flex flex-wrap gap-3">
            {health.services.map((svc) => (
              <div key={svc.name} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
                <StatusBadge
                  status={svc.status === 'connected' ? 'connected' : 'disconnected'}
                  label={svc.name}
                />
                {svc.latency_ms != null && (
                  <span className="text-xs text-[var(--color-text-muted)]">{Math.round(svc.latency_ms)}ms</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Config sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map(({ title, icon: Icon, items }) => (
          <div key={title} className="glass-card p-5">
            <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
              <Icon size={14} /> {title}
            </h3>
            <div className="space-y-2">
              {items.map(({ label, value, mono }) => (
                <div key={label} className="flex items-center justify-between py-1.5 border-b border-[var(--color-border)]/40 last:border-0">
                  <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
                  <span className={`text-sm ${mono ? 'font-mono text-[var(--color-accent-blue)]' : 'text-[var(--color-text-primary)] font-medium'}`}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {health?.uptime_seconds != null && (
        <p className="text-xs text-[var(--color-text-muted)] text-right">
          Uptime: {Math.floor(health.uptime_seconds / 3600)}h {Math.floor((health.uptime_seconds % 3600) / 60)}m
          · Last refreshed: {lastRefresh.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
