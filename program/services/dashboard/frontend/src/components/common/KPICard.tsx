import type { LucideIcon } from 'lucide-react';
import AnimatedNumber from './AnimatedNumber';
import { SkeletonCard } from './Skeleton';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'green' | 'red' | 'blue' | 'yellow' | 'purple' | 'cyan';
  trend?: 'up' | 'down' | 'neutral';
  /** If true, animate value as a number. Provide raw number for best results. */
  animated?: boolean;
  animatedValue?: number;
  animatedPrefix?: string;
  animatedSuffix?: string;
  animatedDecimals?: number;
  sparkline?: number[];
  loading?: boolean;
}

const colorMap: Record<string, string> = {
  green:  'text-[var(--color-accent-green)]',
  red:    'text-[var(--color-accent-red)]',
  blue:   'text-[var(--color-accent-blue)]',
  yellow: 'text-[var(--color-accent-yellow)]',
  purple: 'text-[var(--color-accent-purple)]',
  cyan:   'text-[var(--color-accent-cyan)]',
};

const bgMap: Record<string, string> = {
  green:  'bg-[var(--color-accent-green)]/10',
  red:    'bg-[var(--color-accent-red)]/10',
  blue:   'bg-[var(--color-accent-blue)]/10',
  yellow: 'bg-[var(--color-accent-yellow)]/10',
  purple: 'bg-[var(--color-accent-purple)]/10',
  cyan:   'bg-[var(--color-accent-cyan)]/10',
};

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 24;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} className="opacity-60">
      <polyline
        points={pts.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'blue',
  animated,
  animatedValue,
  animatedPrefix = '',
  animatedSuffix = '',
  animatedDecimals = 2,
  sparkline,
  loading,
}: KPICardProps) {
  if (loading) return <SkeletonCard />;

  const colorClass = colorMap[color] ?? colorMap.blue;
  const bgClass = bgMap[color] ?? bgMap.blue;

  const sparklineColor: Record<string, string> = {
    green: '#10b981', red: '#ef4444', blue: '#3b82f6',
    yellow: '#f59e0b', purple: '#8b5cf6', cyan: '#06b6d4',
  };

  return (
    <div className="glass-card p-5 flex items-start gap-4 animate-fade-in">
      <div className={`p-2.5 rounded-xl ${bgClass} ${colorClass} flex-shrink-0`}>
        <Icon size={20} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">{title}</p>
        <div className="flex items-end justify-between mt-1">
          <p className="text-2xl font-semibold truncate">
            {animated && animatedValue !== undefined ? (
              <AnimatedNumber
                value={animatedValue}
                prefix={animatedPrefix}
                suffix={animatedSuffix}
                decimals={animatedDecimals}
              />
            ) : (
              value
            )}
          </p>
          {sparkline && sparkline.length > 1 && (
            <Sparkline data={sparkline} color={sparklineColor[color] ?? '#3b82f6'} />
          )}
        </div>
        {subtitle && (
          <p className="text-xs text-[var(--color-text-secondary)] mt-1">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
