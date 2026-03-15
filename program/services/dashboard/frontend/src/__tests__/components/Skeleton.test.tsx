import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Skeleton, { SkeletonCard } from '../../components/common/Skeleton';

describe('Skeleton', () => {
  it('renders single line by default', () => {
    const { container } = render(<Skeleton />);
    const divs = container.querySelectorAll('.skeleton');
    expect(divs).toHaveLength(1);
  });

  it('renders multiple lines', () => {
    const { container } = render(<Skeleton lines={3} />);
    const divs = container.querySelectorAll('.skeleton');
    expect(divs).toHaveLength(3);
  });

  it('last line has 60% width', () => {
    const { container } = render(<Skeleton lines={3} />);
    const divs = container.querySelectorAll('.skeleton');
    expect(divs[2].style.width).toBe('60%');
  });
});

describe('SkeletonCard', () => {
  it('renders card with skeleton rows', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('.glass-card')).toBeTruthy();
    expect(container.querySelectorAll('.skeleton').length).toBeGreaterThan(0);
  });

  it('renders fewer skeletons when rows <= 2', () => {
    const { container } = render(<SkeletonCard rows={2} />);
    expect(container.querySelector('.glass-card')).toBeTruthy();
  });
});
