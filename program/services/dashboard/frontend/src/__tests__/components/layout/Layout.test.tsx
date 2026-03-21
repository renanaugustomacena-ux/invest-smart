import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Layout from '../../../components/layout/Layout';
import { useUIStore } from '../../../store/uiStore';
import { useTradingStore } from '../../../store/tradingStore';

describe('Layout', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    useUIStore.setState({
      sidebarCollapsed: false,
      theme: 'dark',
      toasts: [],
      notifications: [],
      unreadCount: 0,
      paletteOpen: false,
    });
    useTradingStore.setState({ overview: null, wsConnected: false });
  });

  const renderLayout = (initialPath = '/') =>
    render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<div data-testid="page-content">Overview Page</div>} />
            <Route path="trading" element={<div data-testid="page-content">Trading Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

  it('renders Sidebar with navigation', () => {
    renderLayout();
    // Both Sidebar and Header contain "MONEYMAKER"
    const brandElements = screen.getAllByText('MONEYMAKER');
    expect(brandElements.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  });

  it('renders Header with WS status', () => {
    renderLayout();
    // Header shows "Reconnecting..." when disconnected
    expect(screen.getByText('Reconnecting…')).toBeInTheDocument();
  });

  it('renders main content area with Outlet', () => {
    renderLayout('/');
    expect(screen.getByTestId('page-content')).toBeInTheDocument();
    expect(screen.getByText('Overview Page')).toBeInTheDocument();
  });

  it('renders correct content for different routes', () => {
    renderLayout('/trading');
    expect(screen.getByText('Trading Page')).toBeInTheDocument();
  });

  it('renders main element for content', () => {
    renderLayout();
    const main = document.querySelector('main');
    expect(main).toBeTruthy();
  });

  it('adjusts margin when sidebar is collapsed', () => {
    useUIStore.setState({ sidebarCollapsed: true });
    renderLayout();
    // When collapsed, sidebar should show expand button
    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
  });
});
