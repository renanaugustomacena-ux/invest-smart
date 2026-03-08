import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  retry = () => this.setState({ hasError: false, error: null });

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="glass-card p-8 text-center space-y-3">
          <AlertTriangle size={32} className="mx-auto text-[var(--color-accent-yellow)]" />
          <p className="text-sm text-[var(--color-text-secondary)]">
            Something went wrong in this section.
          </p>
          {this.state.error && (
            <code className="block text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-secondary)] px-3 py-2 rounded">
              {this.state.error.message}
            </code>
          )}
          <button
            onClick={this.retry}
            className="mt-2 px-4 py-2 rounded-lg bg-[var(--color-accent-blue)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
