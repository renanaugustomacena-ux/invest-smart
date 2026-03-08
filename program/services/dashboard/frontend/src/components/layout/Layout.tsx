import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useUIStore } from '../../store/uiStore';
import { useTradingStore } from '../../store/tradingStore';

export default function Layout() {
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);
  const wsConnected = useTradingStore((s) => s.wsConnected);

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <Sidebar />
      <div
        className="transition-all duration-200"
        style={{ marginLeft: sidebarCollapsed ? '4rem' : '14rem' }}
      >
        <Header wsConnected={wsConnected} />
        <main className="p-6 animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
