import { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, type IChartApi, type CandlestickData, type Time } from 'lightweight-charts';
import { fetchApi } from '../api/client';
import type { OHLCVBar } from '../api/types';

export default function MarketDataPage() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('M5');

  useEffect(() => {
    fetchApi<{ symbols: string[] }>('/api/market/symbols').then((res) => {
      setSymbols(res.symbols);
      if (res.symbols.length > 0) {
        setSelectedSymbol(prev => prev || res.symbols[0]);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!chartRef.current || !selectedSymbol) return;

    if (chartInstance.current) {
      chartInstance.current.remove();
    }

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: '#0a0e17' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1a2332' },
        horzLines: { color: '#1a2332' },
      },
      crosshair: { mode: 0 },
      timeScale: { borderColor: '#2d3748', timeVisible: true },
      rightPriceScale: { borderColor: '#2d3748' },
    });
    chartInstance.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    fetchApi<{ bars: OHLCVBar[] }>(`/api/market/bars?symbol=${selectedSymbol}&timeframe=${timeframe}&limit=500`)
      .then((res) => {
        const data: CandlestickData<Time>[] = res.bars.map((b: OHLCVBar) => ({
          time: (new Date(b.time).getTime() / 1000) as Time,
          open: parseFloat(b.open),
          high: parseFloat(b.high),
          low: parseFloat(b.low),
          close: parseFloat(b.close),
        }));
        candleSeries.setData(data);
        chart.timeScale().fitContent();
      })
      .catch(() => {});

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [selectedSymbol, timeframe]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Market Data</h1>
        <div className="flex items-center gap-3">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-[var(--color-bg-card)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)]"
          >
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <div className="flex gap-1">
            {['M1', 'M5', 'M15', 'H1', 'H4', 'D1'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  timeframe === tf
                    ? 'bg-[var(--color-accent-blue)] text-white'
                    : 'bg-[var(--color-bg-card)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="glass-card p-4">
        <div ref={chartRef} />
        {symbols.length === 0 && (
          <div className="flex items-center justify-center h-[500px] text-[var(--color-text-muted)]">
            No market data available. Start the data ingestion service.
          </div>
        )}
      </div>
    </div>
  );
}
