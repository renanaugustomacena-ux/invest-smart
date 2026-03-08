import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Activity } from 'lucide-react';
import KPICard from '../components/common/KPICard';

describe('KPICard', () => {
  it('renders title and value', () => {
    render(<KPICard title="Daily P&L" value="$120.50" icon={Activity} />);
    expect(screen.getByText('Daily P&L')).toBeInTheDocument();
    expect(screen.getByText('$120.50')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<KPICard title="Signals" value="5" subtitle="today" icon={Activity} />);
    expect(screen.getByText('today')).toBeInTheDocument();
  });

  it('renders skeleton when loading', () => {
    const { container } = render(<KPICard title="Test" value="0" icon={Activity} loading />);
    // Should not render the title when loading
    expect(screen.queryByText('Test')).not.toBeInTheDocument();
    // Should render skeleton placeholder
    expect(container.querySelector('.skeleton')).toBeTruthy();
  });
});
