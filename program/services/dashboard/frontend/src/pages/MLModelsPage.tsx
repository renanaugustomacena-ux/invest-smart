import { useEffect, useState } from 'react';
import { Brain, ExternalLink, Cpu, CheckCircle, XCircle } from 'lucide-react';
import DataTable from '../components/common/DataTable';
import StatusBadge from '../components/common/StatusBadge';
import EmptyState from '../components/common/EmptyState';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { SkeletonCard } from '../components/common/Skeleton';
import { fetchApi } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface MLData {
  models: Record<string, any>[];
  tensorboard_online: boolean;
  tensorboard_url?: string;
  recent_predictions: Record<string, any>[];
  training_metrics: Record<string, any>[];
}

const TB_URL = 'http://localhost:6006';

export default function MLModelsPage() {
  const [data, setData] = useState<MLData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchApi<MLData>('/api/ml');
        setData(res);
        setLoading(false);
      } catch { /* ignore */ }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  const modelColumns = [
    { key: 'model_type',    header: 'Type' },
    { key: 'model_version', header: 'Version' },
    {
      key: 'is_active', header: 'Status',
      render: (row: any) => {
        const active = row.is_active === true || row.is_active === 'True';
        return (
          <StatusBadge
            status={active ? 'connected' : 'disconnected'}
            label={active ? 'Active' : 'Inactive'}
          />
        );
      },
    },
    {
      key: 'validation_accuracy', header: 'Accuracy',
      render: (row: any) => {
        const a = parseFloat(row.validation_accuracy ?? '0');
        return isNaN(a) ? '-' : `${(a * 100).toFixed(1)}%`;
      },
    },
    {
      key: 'created_at', header: 'Created',
      render: (row: any) => new Date(row.created_at).toLocaleDateString(),
    },
  ];

  const predColumns = [
    { key: 'symbol', header: 'Symbol' },
    {
      key: 'direction', header: 'Direction',
      render: (row: any) => (
        <span className={
          row.direction === 'BUY' ? 'text-[var(--color-accent-green)] font-medium'
          : row.direction === 'SELL' ? 'text-[var(--color-accent-red)] font-medium'
          : 'text-[var(--color-text-muted)]'
        }>
          {row.direction}
        </span>
      ),
    },
    {
      key: 'confidence', header: 'Confidence',
      render: (row: any) => {
        const c = parseFloat(row.confidence ?? '0');
        const pct = c <= 1 ? c * 100 : c;
        return <span>{pct.toFixed(1)}%</span>;
      },
    },
    { key: 'model_version',    header: 'Model' },
    { key: 'inference_time_us', header: 'Latency (µs)' },
  ];

  // Confidence histogram data
  const confData = (data?.recent_predictions ?? []).reduce<Record<string, number>>((acc, p) => {
    const c = parseFloat(p.confidence ?? '0');
    const pct = c <= 1 ? c * 100 : c;
    const bucket = `${Math.floor(pct / 10) * 10}-${Math.floor(pct / 10) * 10 + 9}%`;
    acc[bucket] = (acc[bucket] ?? 0) + 1;
    return acc;
  }, {});
  const histogram = Object.entries(confData).map(([range, count]) => ({ range, count }));

  const tbUrl = data?.tensorboard_url ?? TB_URL;
  const tbOnline = data?.tensorboard_online ?? false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <Brain size={22} />
          ML Models
        </h1>
      </div>

      {/* TensorBoard */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] flex items-center gap-2">
            <Cpu size={14} /> TensorBoard
          </h2>
          <div className="flex items-center gap-3">
            {tbOnline ? (
              <span className="flex items-center gap-1.5 text-xs text-[var(--color-accent-green)]">
                <CheckCircle size={13} /> Online
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
                <XCircle size={13} /> Offline
              </span>
            )}
            <a
              href={tbUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
            >
              Open <ExternalLink size={11} />
            </a>
          </div>
        </div>

        {tbOnline ? (
          <iframe
            src={tbUrl}
            className="w-full rounded-xl border border-[var(--color-border)]"
            style={{ height: 560 }}
            title="TensorBoard"
            sandbox="allow-scripts allow-same-origin allow-forms"
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-40 text-[var(--color-text-muted)] gap-3">
            <Brain size={32} className="opacity-30" />
            <p className="text-sm">TensorBoard is not running</p>
            <code className="text-xs bg-[var(--color-bg-secondary)] px-3 py-1.5 rounded border border-[var(--color-border)]">
              tensorboard --logdir /data/tensorboard/logs --port 6006
            </code>
            <a
              href={tbUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
            >
              Try opening TensorBoard <ExternalLink size={11} />
            </a>
          </div>
        )}
      </div>

      {/* Model registry */}
      <ErrorBoundary>
        <div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-3">Model Registry</h2>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : data?.models.length ? (
            <DataTable columns={modelColumns} data={data.models} />
          ) : (
            <div className="glass-card">
              <EmptyState icon={Brain} title="No models registered" description="Train a model to see it here" />
            </div>
          )}
        </div>
      </ErrorBoundary>

      {/* Prediction confidence histogram */}
      {histogram.length > 0 && (
        <div className="glass-card p-5">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">Prediction Confidence Distribution</h2>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={histogram}>
              <XAxis dataKey="range" tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {histogram.map((_, i) => (
                  <Cell key={i} fill="#3b82f6" fillOpacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent predictions */}
      <ErrorBoundary>
        <div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-3">Recent Predictions</h2>
          {data?.recent_predictions.length ? (
            <DataTable columns={predColumns} data={data.recent_predictions} />
          ) : (
            <div className="glass-card">
              <EmptyState icon={Cpu} title="No predictions yet" />
            </div>
          )}
        </div>
      </ErrorBoundary>
    </div>
  );
}
