import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import CommandPalette from '../../components/common/CommandPalette';
import { useUIStore } from '../../store/uiStore';

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ paletteOpen: false, theme: 'dark' });
  });

  it('returns null when closed', () => {
    const { container } = render(
      <MemoryRouter><CommandPalette /></MemoryRouter>
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders palette items when open', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Trading')).toBeInTheDocument();
    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search pages or actions…')).toBeInTheDocument();
  });

  it('filters items by query', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');
    fireEvent.change(input, { target: { value: 'risk' } });
    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.queryByText('Logs')).not.toBeInTheDocument();
  });

  it('shows no results for invalid query', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');
    fireEvent.change(input, { target: { value: 'zzzzzzz' } });
    expect(screen.getByText('No results')).toBeInTheDocument();
  });

  it('handles keyboard navigation', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    fireEvent.keyDown(input, { key: 'Enter' });
    // Should navigate without errors
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('closes on backdrop click', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const backdrop = document.querySelector('.palette-backdrop');
    if (backdrop) fireEvent.click(backdrop);
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('registers Ctrl+K shortcut', () => {
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(useUIStore.getState().paletteOpen).toBe(true);
  });

  it('closes on Escape', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });
});
