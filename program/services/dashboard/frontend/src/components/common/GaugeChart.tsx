import { useEffect, useRef, useState } from 'react';

interface GaugeChartProps {
  value: number;
  max?: number;
  label: string;
  /** Override the arc colour. Defaults to traffic-light based on pct. */
  color?: string;
  size?: number;
}

/** Returns a hex colour based on percentage (green < 60%, yellow < 80%, red ≥ 80%). */
function trafficColor(pct: number): string {
  if (pct < 0.6) return '#10b981';
  if (pct < 0.8) return '#f59e0b';
  return '#ef4444';
}

export default function GaugeChart({ value, max = 100, label, color, size = 100 }: GaugeChartProps) {
  const [animated, setAnimated] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const target = Math.min(Math.max(value, 0), max);
    const start = performance.now();
    const from = animated;

    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);

    const step = (now: number) => {
      const progress = Math.min((now - start) / 600, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimated(from + (target - from) * eased);
      if (progress < 1) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);

    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, max]);

  const pct = Math.min(Math.max(animated / max, 0), 1);
  const R = 36;
  const CX = 44;
  const CY = 48;
  const arcLen = Math.PI * R; // semicircle circumference

  // Path: upper semicircle from (CX-R, CY) → (CX+R, CY) going through (CX, CY-R)
  // sweep=1 (clockwise in SVG) gives the upper arc.
  const trackPath = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;

  const gaugeColor = color ?? trafficColor(pct);
  const dashOffset = arcLen * (1 - pct);

  const displayValue = Math.round((animated / max) * 100);

  return (
    <div className="flex flex-col items-center gap-1" style={{ width: size }}>
      <svg
        viewBox={`0 0 ${CX * 2} ${CY + 6}`}
        width={size}
        height={Math.round(size * 0.6)}
        aria-label={`${label}: ${displayValue}%`}
      >
        {/* Track */}
        <path
          d={trackPath}
          fill="none"
          stroke="var(--color-bg-secondary)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={trackPath}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={arcLen}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.05s linear, stroke 0.3s ease' }}
        />
        {/* Centre label */}
        <text
          x={CX}
          y={CY - 4}
          textAnchor="middle"
          fontSize="13"
          fontWeight="700"
          fill="var(--color-text-primary)"
        >
          {displayValue}%
        </text>
      </svg>
      <span className="text-xs text-[var(--color-text-muted)] text-center leading-tight">{label}</span>
    </div>
  );
}
