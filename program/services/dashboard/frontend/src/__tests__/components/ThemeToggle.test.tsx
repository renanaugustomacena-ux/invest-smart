import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import ThemeToggle from '../../components/common/ThemeToggle';
import { useUIStore } from '../../store/uiStore';

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ theme: 'dark' });
  });

  it('renders with dark theme label', () => {
    render(<ThemeToggle />);
    expect(screen.getByLabelText('Switch to light theme')).toBeInTheDocument();
  });

  it('toggles theme on click', () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole('button'));
    expect(useUIStore.getState().theme).toBe('light');
    expect(screen.getByLabelText('Switch to dark theme')).toBeInTheDocument();
  });
});
