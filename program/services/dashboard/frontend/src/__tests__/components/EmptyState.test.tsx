import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AlertTriangle } from 'lucide-react';
import EmptyState from '../../components/common/EmptyState';

describe('EmptyState', () => {
  it('renders default title', () => {
    render(<EmptyState />);
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('renders custom title and description', () => {
    render(<EmptyState title="No results" description="Try another search" />);
    expect(screen.getByText('No results')).toBeInTheDocument();
    expect(screen.getByText('Try another search')).toBeInTheDocument();
  });

  it('accepts custom icon', () => {
    const { container } = render(<EmptyState icon={AlertTriangle} title="Warning" />);
    expect(container).toBeTruthy();
    expect(screen.getByText('Warning')).toBeInTheDocument();
  });
});
