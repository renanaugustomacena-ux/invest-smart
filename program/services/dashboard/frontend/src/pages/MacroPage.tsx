import { useEffect, useState } from 'react';
import { Globe, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import KPICard from '../components/common/KPICard';
import GaugeChart from '../components/common/GaugeChart';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { SkeletonCard } from '../components/common/Skeleton';
import { fetchApi } from '../api/client';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface MacroSnapshotData {
  vix_spot?: string;
  vix_regime?: string;
  vix_contango?: boolean;
  yield_slope?: string;
  curve_inverted?: boolean;
  real_rate_10y?: string;
  dxy_value?: string;
  dxy_trend?: string;
  recession_prob?: string;
  updated_at?: string;
}

interface VixHistory { recorded_at: string; value: string; }
interface DxyHistory { recorded_at: string; value: string; }

export default function MacroPage() {
  const [snap, setSnap] = useState<MacroSnapshotData | null>(null);
  const [vixHistory, setVixHistory] = useState<VixHistory[]>([]);
  const [dxyHistory, setDxyHistory] = useState<DxyHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [sRes, vRes, dRes] = await Promise.all([
          fetchApi<{ snapshot: MacroSnapshotData | null }>('/api/macro/snapshot'),
          fetchApi<{ data: VixHistory[] }>('/api/macro/vix?limit=60').catch(() => ({ data: [] })),
          fetchApi<{ data: DxyHistory[] }>('/api/macro/dxy?limit=60').catch(() => ({ data: [] })),
        ]);
        setSnap(sRes.snapshot);
        setVixHistory(vRes.data ?? []);
        setDxyHistory(dRes.data ?? []);
        setLoading(false);
      } catch { /* external data may not be populated */ }
    };
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const vix = snap?.vix_spot ? parseFloat(snap.vix_spot) : null;
  const vixReg = vix !== null ? (vix < 20 ? 'Low' : vix < 30 ? 'Elevated' : 'Fear') : null;
  const recProb = snap?.recession_prob ? parseFloat(snap.recession_prob) : null;

  const chartStyle = {
    tick: { fill: 'var(--color-text-muted)', fontSize: 11 },
    axisLine: false,
    tickLine: false,
  };

  const tooltipStyle = {
    contentStyle: {
      background: 'var(--color-bg-card)',
      border: '1px solid var(--color-border)',
      borderRadius: 8,
      fontSize: 12,
    },
    labelStyle: { color: 'var(--color-text-muted)' },
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2">
        <Globe size={22} />
        Macro Indicators
      </h1>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !snap ? (
        <div className="glass-card p-8 text-center text-[var(--color-text-muted)]">
          <Globe size={32} className="mx-auto mb-3 opacity-30" />
          <p>No macro data available.</p>
          <p className="text-xs mt-2">The external data service must populate the macro tables.</p>
        </div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <ErrorBoundary>
              <KPICard
                title="VIX Spot"
                value={snap.vix_spot ?? '-'}
                subtitle={vixReg ?? undefined}
                icon={AlertTriangle}
                color={vix !== null ? (vix < 20 ? 'green' : vix < 30 ? 'yellow' : 'red') : 'blue'}
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="Yield Spread (2s10s)"
                value={snap.yield_slope ?? '-'}
                subtitle={snap.curve_inverted ? '⚠ INVERTED' : 'Normal'}
                icon={snap.curve_inverted ? TrendingDown : TrendingUp}
                color={snap.curve_inverted ? 'red' : 'green'}
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="DXY (Dollar Index)"
                value={snap.dxy_value ?? '-'}
                subtitle={`Trend: ${snap.dxy_trend === '1' ? 'Bullish' : snap.dxy_trend === '-1' ? 'Bearish' : 'Neutral'}`}
                icon={Globe}
                color="blue"
              />
            </ErrorBoundary>
            <ErrorBoundary>
              <KPICard
                title="Recession Probability"
                value={recProb != null ? `${recProb.toFixed(1)}%` : '-'}
                icon={AlertTriangle}
                color={recProb != null ? (recProb > 30 ? 'red' : 'green') : 'blue'}
              />
            </ErrorBoundary>
          </div>

          {/* Gauges */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {vix !== null && (
              <div className="glass-card p-5 flex flex-col items-center gap-2">
                <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">VIX Gauge</p>
                <GaugeChart
                  value={Math.min(vix, 80)}
                  max={80}
                  label={`${vix.toFixed(1)} · ${vixReg}`}
                  color={vix < 20 ? '#10b981' : vix < 30 ? '#f59e0b' : '#ef4444'}
                  size={100}
                />
              </div>
            )}
            {recProb !== null && (
              <div className="glass-card p-5 flex flex-col items-center gap-2">
                <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Recession Prob</p>
                <GaugeChart
                  value={recProb}
                  max={100}
                  label={`${recProb.toFixed(1)}%`}
                  color={recProb > 30 ? '#ef4444' : recProb > 15 ? '#f59e0b' : '#10b981'}
                  size={100}
                />
              </div>
            )}
            <div className="glass-card p-5">
              <h3 className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Details</h3>
              <div className="space-y-2 text-sm">
                {snap.real_rate_10y != null && (
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Real Rate 10Y</span>
                    <span>{snap.real_rate_10y}%</span>
                  </div>
                )}
                {snap.vix_contango != null && (
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">VIX Contango</span>
                    <span>{snap.vix_contango ? 'Yes' : 'No'}</span>
                  </div>
                )}
                {snap.updated_at && (
                  <div className="flex justify-between">
                    <span className="text-[var(--color-text-muted)]">Updated</span>
                    <span className="text-xs">{new Date(snap.updated_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* VIX history chart */}
          {vixHistory.length > 1 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">VIX History</h3>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={vixHistory.map((d) => ({ t: d.recorded_at.slice(0, 10), v: parseFloat(d.value) }))}>
                  <defs>
                    <linearGradient id="vixGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="t" tick={chartStyle.tick} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={chartStyle.tick} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Area type="monotone" dataKey="v" stroke="#f59e0b" fill="url(#vixGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* DXY history chart */}
          {dxyHistory.length > 1 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">DXY History</h3>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={dxyHistory.map((d) => ({ t: d.recorded_at.slice(0, 10), v: parseFloat(d.value) }))}>
                  <defs>
                    <linearGradient id="dxyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="t" tick={chartStyle.tick} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={chartStyle.tick} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Area type="monotone" dataKey="v" stroke="#3b82f6" fill="url(#dxyGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
