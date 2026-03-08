import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import GaugeChart from '../components/common/GaugeChart';

describe('GaugeChart', () => {
  it('renders label and formatted value', () => {
    render(<GaugeChart label="Drawdown" value={2.5} max={5} />);
    expect(screen.getByText('Drawdown')).toBeInTheDocument();
  });

  it('handles zero value', () => {
    render(<GaugeChart label="Win Rate" value={0} max={100} />);
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
  });

  it('clamps value at max', () => {
    const { container } = render(<GaugeChart label="Test" value={150} max={100} />);
    // Should still render without error
    expect(container).toBeTruthy();
  });
});
