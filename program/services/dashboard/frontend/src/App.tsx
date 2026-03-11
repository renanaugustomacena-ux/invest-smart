import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import { ToastContainer } from './components/common/Toast';
import CommandPalette from './components/common/CommandPalette';
import { useUIStore } from './store/uiStore';

import OverviewPage   from './pages/OverviewPage';
import TradingPage    from './pages/TradingPage';
import RiskPage       from './pages/RiskPage';
import MarketDataPage from './pages/MarketDataPage';
import MacroPage      from './pages/MacroPage';
import StrategyPage   from './pages/StrategyPage';
import EconomicPage   from './pages/EconomicPage';
import LogsPage       from './pages/LogsPage';
import ConfigPage     from './pages/ConfigPage';

function ThemeInitializer() {
  const theme = useUIStore((s) => s.theme);
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeInitializer />
      <CommandPalette />
      <ToastContainer />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/"          element={<OverviewPage />} />
          <Route path="/trading"   element={<TradingPage />} />
          <Route path="/risk"      element={<RiskPage />} />
          <Route path="/market"    element={<MarketDataPage />} />
          <Route path="/macro"     element={<MacroPage />} />
          <Route path="/strategy"  element={<StrategyPage />} />
          <Route path="/economic"  element={<EconomicPage />} />
          <Route path="/logs"      element={<LogsPage />} />
          <Route path="/config"    element={<ConfigPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
