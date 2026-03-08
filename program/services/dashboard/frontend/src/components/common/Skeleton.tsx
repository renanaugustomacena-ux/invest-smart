interface SkeletonProps {
  className?: string;
  lines?: number;
  height?: string;
}

/** Shimmer placeholder shown while data is loading. */
export default function Skeleton({ className = '', lines = 1, height = 'h-4' }: SkeletonProps) {
  if (lines === 1) {
    return <div className={`skeleton ${height} w-full rounded ${className}`} />;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`skeleton ${height} rounded`}
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
}

/** Full-card skeleton wrapper */
export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className="glass-card p-5 space-y-3">
      <Skeleton height="h-4" className="w-1/3" />
      <Skeleton height="h-8" className="w-1/2" />
      {rows > 2 && <Skeleton height="h-3" className="w-2/3" />}
    </div>
  );
}
