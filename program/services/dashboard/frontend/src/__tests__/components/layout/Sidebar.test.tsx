import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../../../components/layout/Sidebar';
import { useUIStore } from '../../../store/uiStore';
import { useTradingStore } from '../../../store/tradingStore';

describe('Sidebar', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({ sidebarCollapsed: false });
    useTradingStore.setState({ wsConnected: false });
  });

  const renderSidebar = (initialPath = '/') =>
    render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Sidebar />
      </MemoryRouter>
    );

  it('renders brand name when expanded', () => {
    renderSidebar();
    expect(screen.getByText('MONEYMAKER')).toBeInTheDocument();
  });

  it('renders all navigation links', () => {
    renderSidebar();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Trading')).toBeInTheDocument();
    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.getByText('Market Data')).toBeInTheDocument();
    expect(screen.getByText('Macro')).toBeInTheDocument();
    expect(screen.getByText('Strategy')).toBeInTheDocument();
    expect(screen.getByText('Economic')).toBeInTheDocument();
    expect(screen.getByText('Logs')).toBeInTheDocument();
    expect(screen.getByText('Config')).toBeInTheDocument();
  });

  it('navigation links have correct hrefs', () => {
    renderSidebar();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = nav.querySelectorAll('a');
    const hrefs = Array.from(links).map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual([
      '/', '/trading', '/risk', '/market', '/macro',
      '/strategy', '/economic', '/logs', '/config',
    ]);
  });

  it('active link is highlighted (Overview at root path)', () => {
    renderSidebar('/');
    const overviewLink = screen.getByText('Overview').closest('a');
    // NavLink with isActive applies the active class containing accent-blue
    expect(overviewLink?.className).toContain('text-[var(--color-accent-blue)]');
  });

  it('active link is highlighted for Trading route', () => {
    renderSidebar('/trading');
    const tradingLink = screen.getByText('Trading').closest('a');
    expect(tradingLink?.className).toContain('text-[var(--color-accent-blue)]');
    // Overview should NOT be active
    const overviewLink = screen.getByText('Overview').closest('a');
    expect(overviewLink?.className).not.toContain('font-medium');
  });

  it('shows Offline when not connected', () => {
    renderSidebar();
    expect(screen.getByText(/Offline/)).toBeInTheDocument();
  });

  it('shows Live when connected', () => {
    useTradingStore.setState({ wsConnected: true });
    renderSidebar();
    expect(screen.getByText(/Live/)).toBeInTheDocument();
  });

  it('toggles sidebar collapse', async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByLabelText('Collapse sidebar'));
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });

  it('collapsed state hides brand name and shows expand button', () => {
    useUIStore.setState({ sidebarCollapsed: true });
    renderSidebar();
    expect(screen.queryByText('MONEYMAKER')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
  });

  it('collapsed state shows icons only (no text labels)', () => {
    useUIStore.setState({ sidebarCollapsed: true });
    renderSidebar();
    // When collapsed, text labels like "Overview", "Trading", etc. are not rendered
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();
    expect(screen.queryByText('Trading')).not.toBeInTheDocument();
    expect(screen.queryByText('Risk')).not.toBeInTheDocument();
    // But navigation links (icons) are still present
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = nav.querySelectorAll('a');
    expect(links.length).toBe(9);
  });

  it('collapsed state shows title attributes on links for tooltip', () => {
    useUIStore.setState({ sidebarCollapsed: true });
    renderSidebar();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = nav.querySelectorAll('a');
    // When collapsed, each NavLink gets a title attribute
    const titles = Array.from(links).map((a) => a.getAttribute('title'));
    expect(titles).toEqual([
      'Overview', 'Trading', 'Risk', 'Market Data', 'Macro',
      'Strategy', 'Economic', 'Logs', 'Config',
    ]);
  });
});
