import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBadge from '../../components/common/StatusBadge';

describe('StatusBadge', () => {
  it('renders connected status with label', () => {
    render(<StatusBadge status="connected" label="Online" />);
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('renders disconnected status with default text', () => {
    render(<StatusBadge status="disconnected" />);
    expect(screen.getByText('disconnected')).toBeInTheDocument();
  });

  it('renders warning status', () => {
    render(<StatusBadge status="warning" label="Degraded" />);
    expect(screen.getByText('Degraded')).toBeInTheDocument();
  });
});
