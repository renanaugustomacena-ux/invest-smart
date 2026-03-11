import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, TrendingUp, ShieldAlert, BarChart3,
  Globe, Target, CalendarDays, FileText, Settings,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { useTradingStore } from '../../store/tradingStore';

const navItems = [
  { path: '/',          label: 'Overview',         icon: LayoutDashboard },
  { path: '/trading',   label: 'Trading',           icon: TrendingUp },
  { path: '/risk',      label: 'Risk',              icon: ShieldAlert },
  { path: '/market',    label: 'Market Data',       icon: BarChart3 },
  { path: '/macro',     label: 'Macro',             icon: Globe },
  { path: '/strategy',  label: 'Strategy',          icon: Target },
  { path: '/economic',  label: 'Economic',          icon: CalendarDays },
  { path: '/logs',      label: 'Logs',              icon: FileText },
  { path: '/config',    label: 'Config',            icon: Settings },
];

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const wsConnected = useTradingStore((s) => s.wsConnected);

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col transition-all duration-200 z-50 ${
        sidebarCollapsed ? 'w-16' : 'w-56'
      }`}
    >
      {/* Logo + collapse */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-[var(--color-border)] flex-shrink-0">
        {!sidebarCollapsed && (
          <span className="text-base font-bold tracking-tight text-[var(--color-accent-blue)]">
            MONEYMAKER
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="ml-auto p-1.5 rounded-lg hover:bg-[var(--color-bg-card)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3 overflow-y-auto" role="navigation" aria-label="Main navigation">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            title={sidebarCollapsed ? label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 mx-2 rounded-xl text-sm transition-all ${
                isActive
                  ? 'bg-[var(--color-accent-blue)]/10 text-[var(--color-accent-blue)] font-medium'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card)] hover:text-[var(--color-text-primary)]'
              } ${sidebarCollapsed ? 'justify-center' : ''}`
            }
          >
            <Icon size={18} className="flex-shrink-0" />
            {!sidebarCollapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[var(--color-border)] flex items-center gap-2 flex-shrink-0">
        <span
          className={`w-2 h-2 rounded-full flex-shrink-0 ${wsConnected ? 'bg-[var(--color-accent-green)] animate-pulse-glow' : 'bg-[var(--color-text-muted)]'}`}
          aria-label={wsConnected ? 'Connected' : 'Disconnected'}
        />
        {!sidebarCollapsed && (
          <span className="text-xs text-[var(--color-text-muted)] truncate">
            {wsConnected ? 'Live' : 'Offline'} · MONEYMAKER V1
          </span>
        )}
      </div>
    </aside>
  );
}
