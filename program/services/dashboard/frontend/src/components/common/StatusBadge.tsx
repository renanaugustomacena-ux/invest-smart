interface StatusBadgeProps {
  status: 'connected' | 'disconnected' | 'warning';
  label?: string;
}

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const styles = {
    connected: 'bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)] border-[var(--color-accent-green)]/20',
    disconnected: 'bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)] border-[var(--color-accent-red)]/20',
    warning: 'bg-[var(--color-accent-yellow)]/10 text-[var(--color-accent-yellow)] border-[var(--color-accent-yellow)]/20',
  };

  const dotStyles = {
    connected: 'bg-[var(--color-accent-green)]',
    disconnected: 'bg-[var(--color-accent-red)]',
    warning: 'bg-[var(--color-accent-yellow)]',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotStyles[status]}`} />
      {label || status}
    </span>
  );
}
