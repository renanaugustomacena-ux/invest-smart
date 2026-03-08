import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  className?: string;
}

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No data',
  description,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
      <Icon size={32} className="text-[var(--color-text-muted)] mb-3" />
      <p className="text-sm font-medium text-[var(--color-text-secondary)]">{title}</p>
      {description && (
        <p className="text-xs text-[var(--color-text-muted)] mt-1 max-w-xs">{description}</p>
      )}
    </div>
  );
}
