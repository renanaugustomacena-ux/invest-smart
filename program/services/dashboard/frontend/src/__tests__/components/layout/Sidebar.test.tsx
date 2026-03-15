import { render, screen, fireEvent } from '@testing-library/react';
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

  const renderSidebar = () =>
    render(
      <MemoryRouter>
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

  it('shows Offline when not connected', () => {
    renderSidebar();
    expect(screen.getByText(/Offline/)).toBeInTheDocument();
  });

  it('shows Live when connected', () => {
    useTradingStore.setState({ wsConnected: true });
    renderSidebar();
    expect(screen.getByText(/Live/)).toBeInTheDocument();
  });

  it('toggles sidebar collapse', () => {
    renderSidebar();
    fireEvent.click(screen.getByLabelText('Collapse sidebar'));
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });

  it('hides brand name when collapsed', () => {
    useUIStore.setState({ sidebarCollapsed: true });
    renderSidebar();
    expect(screen.queryByText('MONEYMAKER')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
  });
});
