import { useEffect, useState } from 'react';
import { ShieldAlert, AlertTriangle, Users, Activity } from 'lucide-react';
import KPICard from '../components/common/KPICard';
import GaugeChart from '../components/common/GaugeChart';
import KillSwitchButton from '../components/common/KillSwitchButton';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { SkeletonCard } from '../components/common/Skeleton';
import { fetchApi } from '../api/client';
import type { RiskMetrics } from '../api/types';

export default function RiskPage() {
  const [risk, setRisk] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await fetchApi<RiskMetrics>('/api/risk');
      setRisk(data);
      setLoading(false);
    } catch { /* backend offline */ }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const dailyLoss = risk ? parseFloat(risk.daily_loss_pct) : 0;
  const drawdown  = risk ? parseFloat(risk.drawdown_pct) : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2">
        <ShieldAlert size={22} />
        Risk Management
      </h1>

      {/* Kill switch — full card */}
      <ErrorBoundary>
        <KillSwitchButton
          active={risk?.kill_switch_active ?? false}
          reason={risk?.kill_switch_reason}
          onToggle={() => load()}
        />
      </ErrorBoundary>

      {/* Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ErrorBoundary>
          <div className="glass-card p-5 flex flex-col items-center gap-2">
            <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Daily Loss</p>
            <GaugeChart
              value={dailyLoss}
              max={2}
              label="/ 2.0% limit"
              color={dailyLoss > 1.8 ? '#ef4444' : dailyLoss > 1.5 ? '#f59e0b' : '#10b981'}
              size={100}
            />
          </div>
        </ErrorBoundary>

        <ErrorBoundary>
          <div className="glass-card p-5 flex flex-col items-center gap-2">
            <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Drawdown</p>
            <GaugeChart
              value={drawdown}
              max={5}
              label="/ 5.0% limit"
              color={drawdown > 4 ? '#ef4444' : drawdown > 3 ? '#f59e0b' : '#10b981'}
              size={100}
            />
          </div>
        </ErrorBoundary>

        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <KPICard
              title="Open Positions"
              value={`${risk?.open_positions ?? 0} / ${risk?.max_positions ?? 5}`}
              icon={Users}
              color={risk && risk.open_positions >= (risk.max_positions ?? 5) ? 'yellow' : 'blue'}
            />
            <KPICard
              title="Market Regime"
              value={risk?.regime ?? 'Unknown'}
              subtitle={`Maturity: ${risk?.maturity_state ?? '-'}`}
              icon={Activity}
              color="purple"
            />
          </>
        )}
      </div>

      {/* Risk KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <KPICard
              title="Daily Loss %"
              value={`${dailyLoss.toFixed(3)}%`}
              subtitle="Circuit breaker at 2.0%"
              icon={AlertTriangle}
              color={dailyLoss > 1.5 ? 'red' : 'green'}
              animated
              animatedValue={dailyLoss}
              animatedSuffix="%"
              animatedDecimals={3}
            />
            <KPICard
              title="Drawdown %"
              value={`${drawdown.toFixed(3)}%`}
              subtitle="Kill switch at 5.0%"
              icon={ShieldAlert}
              color={drawdown > 3 ? 'red' : 'green'}
              animated
              animatedValue={drawdown}
              animatedSuffix="%"
              animatedDecimals={3}
            />
          </>
        )}
      </div>

      {/* Exposed Symbols */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-3">Symbols Exposed</h3>
        {risk?.symbols_exposed && risk.symbols_exposed.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {risk.symbols_exposed.map((sym) => (
              <span
                key={sym}
                className="px-3 py-1 rounded-full text-sm bg-[var(--color-bg-secondary)] text-[var(--color-accent-blue)] border border-[var(--color-accent-blue)]/20"
              >
                {sym}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)]">No active exposure</p>
        )}
      </div>
    </div>
  );
}
