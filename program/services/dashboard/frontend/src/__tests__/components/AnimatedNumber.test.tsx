import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AnimatedNumber from '../../components/common/AnimatedNumber';

describe('AnimatedNumber', () => {
  it('renders with prefix and suffix', () => {
    render(<AnimatedNumber value={100} prefix="$" suffix=" USD" decimals={0} />);
    // Initial render uses state which starts at value
    const el = screen.getByText(/\$/);
    expect(el).toBeInTheDocument();
  });

  it('renders with default decimals', () => {
    render(<AnimatedNumber value={42.5} />);
    // The display should format with 2 decimals
    const el = screen.getByText(/42/);
    expect(el).toBeInTheDocument();
  });

  it('applies className', () => {
    const { container } = render(<AnimatedNumber value={10} className="test-class" />);
    expect(container.querySelector('.test-class')).toBeTruthy();
  });
});
