import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import CommandPalette from '../../components/common/CommandPalette';
import { useUIStore } from '../../store/uiStore';

// Track navigations by spying on the navigate function via MemoryRouter
const mockedNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockedNavigate,
  };
});

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ paletteOpen: false, theme: 'dark' });
    mockedNavigate.mockClear();
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

  it('opens on keyboard shortcut Ctrl+K', () => {
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    expect(useUIStore.getState().paletteOpen).toBe(false);
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(useUIStore.getState().paletteOpen).toBe(true);
  });

  it('opens on keyboard shortcut Cmd+K (metaKey)', () => {
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    expect(useUIStore.getState().paletteOpen).toBe(false);
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    expect(useUIStore.getState().paletteOpen).toBe(true);
  });

  it('typing filters available commands', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);

    const input = screen.getByPlaceholderText('Search pages or actions…');
    await user.type(input, 'risk');

    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.queryByText('Logs')).not.toBeInTheDocument();
    expect(screen.queryByText('Config')).not.toBeInTheDocument();
  });

  it('shows no results for invalid query', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');
    await user.type(input, 'zzzzzzz');
    expect(screen.getByText('No results')).toBeInTheDocument();
  });

  it('selecting a command triggers navigation', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);

    // Click on the "Trading" item directly
    await user.click(screen.getByText('Trading'));
    expect(mockedNavigate).toHaveBeenCalledWith('/trading');
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('keyboard Enter selects the highlighted command and navigates', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');

    // Arrow down to "Trading" (index 1), then Enter
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockedNavigate).toHaveBeenCalledWith('/trading');
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('Escape closes the palette', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    expect(screen.getByPlaceholderText('Search pages or actions…')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('closes on backdrop click', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const backdrop = document.querySelector('.palette-backdrop');
    expect(backdrop).toBeTruthy();
    if (backdrop) fireEvent.click(backdrop);
    expect(useUIStore.getState().paletteOpen).toBe(false);
  });

  it('handles keyboard navigation ArrowDown/ArrowUp', () => {
    useUIStore.setState({ paletteOpen: true });
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    const input = screen.getByPlaceholderText('Search pages or actions…');
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    fireEvent.keyDown(input, { key: 'Enter' });
    // Should navigate to "Trading" (index 1 after down-down-up)
    expect(mockedNavigate).toHaveBeenCalledWith('/trading');
  });
});
