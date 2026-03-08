import { useEffect, useState } from 'react';
import { Target, TrendingUp, TrendingDown } from 'lucide-react';
import DataTable from '../components/common/DataTable';
import EmptyState from '../components/common/EmptyState';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { SkeletonCard } from '../components/common/Skeleton';
import { fetchApi } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface StrategyRow {
  strategy_name: string;
  symbol?: string;
  day?: string;
  total_signals: number;
  wins: number;
  losses: number;
  total_profit: string;
  avg_confidence: string;
  win_rate: string;
}

export default function StrategyPage() {
  const [summary, setSummary] = useState<StrategyRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchApi<{ data: StrategyRow[] }>('/api/strategy/summary');
        setSummary(res.data ?? []);
        setLoading(false);
      } catch { /* ignore */ }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  const columns = [
    { key: 'strategy_name', header: 'Strategy' },
    { key: 'symbol', header: 'Symbol' },
    { key: 'total_signals', header: 'Signals' },
    {
      key: 'wins', header: 'W / L',
      render: (row: any) => (
        <span className="text-sm">
          <span className="text-[var(--color-accent-green)] font-medium">{row.wins}</span>
          <span className="text-[var(--color-text-muted)]"> / </span>
          <span className="text-[var(--color-accent-red)] font-medium">{row.losses}</span>
        </span>
      ),
    },
    { key: 'win_rate', header: 'Win %', render: (row: any) => `${parseFloat(row.win_rate ?? 0).toFixed(1)}%` },
    {
      key: 'total_profit', header: 'Profit',
      render: (row: any) => {
        const p = parseFloat(row.total_profit ?? '0');
        return (
          <span className={`font-semibold flex items-center gap-1 ${p >= 0 ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}`}>
            {p >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {p.toFixed(2)}
          </span>
        );
      },
    },
    { key: 'avg_confidence', header: 'Avg Conf', render: (row: any) => `${(parseFloat(row.avg_confidence ?? 0) * 100).toFixed(0)}%` },
  ];

  // Build chart data grouped by strategy_name
  const chartData = summary.reduce<Record<string, StrategyRow & { profit: number }>>((acc, row) => {
    if (!acc[row.strategy_name]) {
      acc[row.strategy_name] = { ...row, profit: 0 };
    }
    acc[row.strategy_name].profit += parseFloat(row.total_profit ?? '0');
    return acc;
  }, {});
  const chart = Object.values(chartData).slice(0, 10);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const p = payload[0].value as number;
    return (
      <div className="glass-card px-3 py-2 text-xs">
        <p className="font-medium">{label}</p>
        <p className={p >= 0 ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}>
          P&L: ${p.toFixed(2)}
        </p>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2">
        <Target size={22} />
        Strategy Performance
      </h1>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : summary.length === 0 ? (
        <div className="glass-card">
          <EmptyState
            icon={Target}
            title="No strategy data yet"
            description="Strategy performance will appear here once trades are executed"
          />
        </div>
      ) : (
        <>
          {/* P&L Bar Chart */}
          {chart.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">Strategy P&L Comparison</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chart} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <XAxis
                    dataKey="strategy_name"
                    tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(59,130,246,0.05)' }} />
                  <Bar dataKey="profit" radius={[4, 4, 0, 0]}>
                    {chart.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.profit >= 0 ? '#10b981' : '#ef4444'}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Table */}
          <ErrorBoundary>
            <DataTable columns={columns} data={summary} />
          </ErrorBoundary>
        </>
      )}
    </div>
  );
}
