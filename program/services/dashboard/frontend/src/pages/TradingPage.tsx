import { useCallback, useEffect } from 'react';
import { TrendingUp, Layers } from 'lucide-react';
import DataTable from '../components/common/DataTable';
import KillSwitchButton from '../components/common/KillSwitchButton';
import EmptyState from '../components/common/EmptyState';
import ErrorBoundary from '../components/common/ErrorBoundary';
import { useWebSocket } from '../hooks/useWebSocket';
import { useTradingStore } from '../store/tradingStore';

interface SignalRow {
  symbol: string;
  direction: string;
  confidence: string;
  source_tier: string;
  regime: string;
  created_at: string;
}

interface PositionRow {
  symbol: string;
  side: string;
  quantity: string;
  avg_price: string;
  unrealized_pnl: string;
}

interface WsTradingPayload {
  type: string;
  data: {
    recent_signals: SignalRow[];
    positions: PositionRow[];
    regime: string | null;
  };
}

function ConfidenceBar({ value }: { value: string }) {
  const pct = (() => {
    const n = parseFloat(value ?? '0');
    if (isNaN(n)) return 0;
    return n <= 1 ? n * 100 : n;
  })();
  const color = pct >= 70 ? 'var(--color-accent-green)' : pct >= 50 ? 'var(--color-accent-yellow)' : 'var(--color-accent-red)';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 rounded-full bg-[var(--color-bg-secondary)] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs text-[var(--color-text-muted)]">{pct.toFixed(0)}%</span>
    </div>
  );
}

export default function TradingPage() {
  const { signals, positions, overview, setTradingData, setWsConnected } = useTradingStore();

  const onMessage = useCallback((msg: WsTradingPayload) => {
    if (msg.type === 'trading' && msg.data) {
      setTradingData(
        msg.data.recent_signals ?? [],
        msg.data.positions ?? [],
        msg.data.regime ?? null,
      );
    }
  }, [setTradingData]);

  const { connected } = useWebSocket('/ws/trading', onMessage);

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  const signalColumns = [
    { key: 'symbol', header: 'Symbol' },
    {
      key: 'direction', header: 'Direction',
      render: (row: SignalRow) => (
        <span className={`font-semibold ${
          row.direction === 'BUY' ? 'text-[var(--color-accent-green)]'
          : row.direction === 'SELL' ? 'text-[var(--color-accent-red)]'
          : 'text-[var(--color-text-muted)]'
        }`}>
          {row.direction}
        </span>
      ),
    },
    {
      key: 'confidence', header: 'Confidence',
      render: (row: SignalRow) => <ConfidenceBar value={row.confidence} />,
    },
    { key: 'source_tier', header: 'Source' },
    { key: 'regime',      header: 'Regime' },
    {
      key: 'created_at', header: 'Time',
      render: (row: SignalRow) => (
        <span className="text-xs text-[var(--color-text-muted)]">
          {new Date(row.created_at).toLocaleTimeString()}
        </span>
      ),
    },
  ];

  const positionColumns = [
    { key: 'symbol', header: 'Symbol' },
    {
      key: 'side', header: 'Side',
      render: (row: PositionRow) => (
        <span className={`font-semibold ${row.side === 'LONG' ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}`}>
          {row.side}
        </span>
      ),
    },
    { key: 'quantity',  header: 'Lots' },
    { key: 'avg_price', header: 'Avg Price' },
    {
      key: 'unrealized_pnl', header: 'Unrealised P&L',
      render: (row: PositionRow) => {
        const p = parseFloat(row.unrealized_pnl ?? '0');
        return (
          <span className={`font-semibold ${p >= 0 ? 'text-[var(--color-accent-green)]' : 'text-[var(--color-accent-red)]'}`}>
            {isNaN(p) ? '-' : `$${p.toFixed(2)}`}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <TrendingUp size={22} />
          Trading
        </h1>
        <KillSwitchButton
          compact
          active={overview?.kill_switch_active ?? false}
        />
      </div>

      {/* Positions */}
      <ErrorBoundary>
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Layers size={15} className="text-[var(--color-text-muted)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-muted)]">
              Open Positions ({positions.length})
            </h2>
          </div>
          {positions.length > 0 ? (
            <DataTable columns={positionColumns} data={positions} />
          ) : (
            <div className="glass-card">
              <EmptyState
                icon={Layers}
                title="No open positions"
                description="Positions will appear here when trades are executed"
              />
            </div>
          )}
        </div>
      </ErrorBoundary>

      {/* Signals */}
      <ErrorBoundary>
        <div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-3">
            Recent Signals ({signals.length})
          </h2>
          {signals.length > 0 ? (
            <DataTable columns={signalColumns} data={signals} />
          ) : (
            <div className="glass-card">
              <EmptyState
                icon={TrendingUp}
                title="No signals yet"
                description="Signals generated by the Algo Engine will appear here"
              />
            </div>
          )}
        </div>
      </ErrorBoundary>
    </div>
  );
}
