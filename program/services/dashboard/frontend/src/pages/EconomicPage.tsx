import { useEffect, useState } from 'react';
import { CalendarDays, AlertTriangle, Clock } from 'lucide-react';
import DataTable from '../components/common/DataTable';
import EmptyState from '../components/common/EmptyState';
import { fetchApi } from '../api/client';

interface EconomicEvent {
  event_time: string;
  event_name: string;
  country?: string;
  currency?: string;
  impact?: string;
  forecast?: string;
  previous?: string;
  actual?: string;
}

interface Blackout {
  symbol: string;
  reason?: string;
  blackout_start?: string;
  blackout_end?: string;
}

function ImpactBadge({ impact }: { impact?: string }) {
  const styles: Record<string, string> = {
    high:   'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)] border-[var(--color-accent-red)]/20',
    medium: 'bg-[var(--color-accent-yellow)]/10 text-[var(--color-accent-yellow)] border-[var(--color-accent-yellow)]/20',
    low:    'bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] border-[var(--color-border)]',
  };
  const key = impact?.toLowerCase() ?? 'low';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${styles[key] ?? styles.low}`}>
      {impact ?? 'low'}
    </span>
  );
}

export default function EconomicPage() {
  const [events, setEvents] = useState<EconomicEvent[]>([]);
  const [blackouts, setBlackouts] = useState<Blackout[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [evRes, blRes] = await Promise.all([
          fetchApi<{ events: EconomicEvent[] }>('/api/economic/upcoming'),
          fetchApi<{ blackouts: Blackout[] }>('/api/economic/blackouts'),
        ]);
        setEvents(evRes.events ?? []);
        setBlackouts(blRes.blackouts ?? []);
      } catch { /* ignore */ }
    };
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const eventColumns = [
    {
      key: 'event_time', header: 'Time',
      render: (row: EconomicEvent) => (
        <div className="flex items-center gap-1.5 text-xs">
          <Clock size={11} className="text-[var(--color-text-muted)]" />
          <span>{new Date(row.event_time).toLocaleString()}</span>
        </div>
      ),
    },
    { key: 'event_name', header: 'Event' },
    { key: 'currency',   header: 'Currency' },
    {
      key: 'impact', header: 'Impact',
      render: (row: EconomicEvent) => <ImpactBadge impact={row.impact} />,
    },
    { key: 'forecast', header: 'Forecast', render: (row: EconomicEvent) => row.forecast ?? '-' },
    { key: 'previous', header: 'Previous', render: (row: EconomicEvent) => row.previous ?? '-' },
    { key: 'actual',   header: 'Actual',   render: (row: EconomicEvent) => row.actual ?? '-' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2">
        <CalendarDays size={22} />
        Economic Calendar
      </h1>

      {/* Active blackout banner */}
      {blackouts.length > 0 && (
        <div className="glass-card p-4 border-l-4 border-l-[var(--color-accent-red)] bg-[var(--color-accent-red)]/5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-[var(--color-accent-red)]" />
            <h3 className="text-sm font-semibold text-[var(--color-accent-red)]">
              Active Trading Blackouts ({blackouts.length})
            </h3>
          </div>
          <div className="space-y-1.5">
            {blackouts.map((b, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="font-medium text-[var(--color-accent-yellow)] min-w-[60px]">{b.symbol}</span>
                <span className="text-[var(--color-text-secondary)]">{b.reason}</span>
                {b.blackout_end && (
                  <span className="text-xs text-[var(--color-text-muted)] ml-auto">
                    until {new Date(b.blackout_end).toLocaleTimeString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Events table */}
      {events.length > 0 ? (
        <DataTable columns={eventColumns} data={events} />
      ) : (
        <div className="glass-card">
          <EmptyState
            icon={CalendarDays}
            title="No upcoming events"
            description="Economic events will appear here when the calendar is populated"
          />
        </div>
      )}
    </div>
  );
}
