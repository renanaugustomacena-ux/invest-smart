import { useCallback, useEffect, useState } from 'react';
import {
  Signal, TrendingUp, ShieldAlert, BarChart3, Activity,
  ExternalLink, AlertTriangle, Layers,
} from 'lucide-react';
import KPICard from '../components/common/KPICard';
import GaugeChart from '../components/common/GaugeChart';
import KillSwitchButton from '../components/common/KillSwitchButton';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { SkeletonCard } from '../components/common/Skeleton';
import { useWebSocket } from '../hooks/useWebSocket';
import { fetchApi } from '../api/client';
import { useTradingStore } from '../store/tradingStore';
import { useSystemStore } from '../store/systemStore';
import type { SystemStatus } from '../api/types';

interface WsOverviewPayload {
  type: string;
  data: {
    signals_today: number;
    daily_pnl: string;
    total_trades_today: number;
    win_rate: string;
    open_positions: number;
    drawdown_pct: string;
    kill_switch_active: boolean;
    regime: string | null;
    redis_status: string;
  };
}

export default function OverviewPage() {
  const { overview, setOverview, setWsConnected } = useTradingStore();
  const { setStatus } = useSystemStore();
  const [services, setServices] = useState<any[]>([]);
  const [recentSignals, setRecentSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // WebSocket overview stream
  const onMessage = useCallback((msg: WsOverviewPayload) => {
    if (msg.type === 'overview' && msg.data) {
      setOverview(msg.data);
      setLoading(false);
    }
  }, [setOverview]);

  const { connected } = useWebSocket('/ws/overview', onMessage);

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  // Fetch system health + recent signals
  useEffect(() => {
    const load = async () => {
      try {
        const [health, overview] = await Promise.all([
          fetchApi<SystemStatus>('/api/system/health'),
          fetchApi<any>('/api/overview'),
        ]);
        setStatus(health);
        setServices(overview?.services ?? []);
        setRecentSignals(overview?.recent_signals ?? []);
      } catch { /* backend may be offline */ }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [setStatus]);

  const kpis = overview;
  const drawdown = kpis ? parseFloat(kpis.drawdown_pct) : 0;
  const winRate  = kpis ? parseFloat(kpis.win_rate) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">System Overview</h1>
        <div className="flex items-center gap-2">
          <span className={`text-xs ${connected ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-text-muted)]'}`}>
            {connected ? '● Live' : '○ Connecting…'}
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <ErrorBoundary>
              <KPICard
                title="Daily P&L"
                value={kpis ? `$${parseFloat(kpis.daily_pnl).toFixed(2)}` : '-'}
                icon={TrendingUp}
                color={kpis && parseFloat(kpis.daily_pnl) >= 0 ? 'green' : 'red'}
                animated
                animatedValue={kpis ? parseFloat(kpis.daily_pnl) : 0}
                animatedPrefix="$"
                animatedDecimals={2}
                subtitle={kpis?.regime ? `Regime: ${kpis.regime}` : undefined}
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="Win Rate"
                value={kpis ? `${winRate.toFixed(1)}%` : '-'}
                icon={BarChart3}
                color="purple"
                animated
                animatedValue={winRate}
                animatedSuffix="%"
                animatedDecimals={1}
                subtitle={`${kpis?.total_trades_today ?? 0} trades today`}
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="Signals Today"
                value={kpis?.signals_today ?? '-'}
                icon={Signal}
                color="blue"
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="Open Positions"
                value={`${kpis?.open_positions ?? 0} / 5`}
                icon={Layers}
                color={kpis && kpis.open_positions >= 4 ? 'yellow' : 'cyan'}
              />
            </ErrorBoundary>
          </>
        )}
      </div>

      {/* Gauges + Kill Switch */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Drawdown gauge */}
        <div className="glass-card p-5 flex flex-col items-center justify-center gap-2">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Drawdown</p>
          <GaugeChart
            value={drawdown}
            max={5}
            label="/ 5% limit"
            color={drawdown > 4 ? '#ef4444' : drawdown > 3 ? '#f59e0b' : '#10b981'}
            size={96}
          />
        </div>

        {/* Win rate gauge */}
        <div className="glass-card p-5 flex flex-col items-center justify-center gap-2">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Win Rate</p>
          <GaugeChart
            value={winRate}
            max={100}
            label="% win rate"
            color={winRate >= 55 ? '#10b981' : winRate >= 45 ? '#f59e0b' : '#ef4444'}
            size={96}
          />
        </div>

        {/* Open positions gauge */}
        <div className="glass-card p-5 flex flex-col items-center justify-center gap-2">
          <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Positions</p>
          <GaugeChart
            value={kpis?.open_positions ?? 0}
            max={5}
            label="/ 5 max"
            size={96}
          />
        </div>

        {/* Kill switch */}
        <KillSwitchButton
          active={kpis?.kill_switch_active ?? false}
        />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="glass-card px-5 py-4 flex items-center justify-between hover:border-[var(--color-accent-blue)]/50 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <Activity size={18} className="text-[var(--color-accent-orange, #f97316)]" style={{ color: '#f97316' }} />
            <div>
              <p className="text-sm font-medium">Grafana</p>
              <p className="text-xs text-[var(--color-text-muted)]">Metrics &amp; dashboards</p>
            </div>
          </div>
          <ExternalLink size={14} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-accent-blue)] transition-colors" />
        </a>
      </div>

      {/* Service Health */}
      {services.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">Service Health</h3>
          <div className="flex flex-wrap gap-3">
            {services.map((svc) => (
              <div
                key={svc.name}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
              >
                <Activity
                  size={13}
                  className={svc.status === 'connected' ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}
                />
                <span className="text-sm">{svc.name}</span>
                {svc.latency_ms != null && (
                  <span className="text-xs text-[var(--color-text-muted)]">{Math.round(svc.latency_ms)}ms</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Signals */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">Recent Signals</h3>
        {recentSignals.length > 0 ? (
          <div className="space-y-2">
            {recentSignals.slice(0, 6).map((sig, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 px-3 rounded-xl bg-[var(--color-bg-secondary)] animate-fade-in"
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-lg ${
                    sig.direction === 'BUY'
                      ? 'bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]'
                      : sig.direction === 'SELL'
                      ? 'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)]'
                      : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)]'
                  }`}>
                    {sig.direction}
                  </span>
                  <span className="text-sm font-medium">{sig.symbol}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
                  <span>
                    {(() => {
                      const c = parseFloat(sig.confidence ?? '0');
                      return isNaN(c) ? sig.confidence : (c * 100 < 2 ? (c * 100).toFixed(0) + '%' : c.toFixed(2));
                    })()}
                  </span>
                  {sig.source_tier && <span className="hidden sm:block">{sig.source_tier}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 py-4 text-sm text-[var(--color-text-muted)]">
            <AlertTriangle size={16} />
            <span>No signals yet — system may be warming up</span>
          </div>
        )}
      </div>
    </div>
  );
}
