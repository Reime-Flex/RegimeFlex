'use client';

import { StatusIndicator } from './components/StatusIndicator';
import { PriceChart } from './components/PriceChart';
import { IndicatorPanels } from './components/IndicatorPanels';
import { PortfolioCard } from './components/PortfolioCard';
import { PositionsTable } from './components/PositionsTable';
import { MarketContext } from './components/MarketContext';
import { RegimePanel } from './components/RegimePanel';
import { useRegime } from './context/RegimeContext';

// Backend URL - uses Next.js API proxy routes
const BACKEND_URL = '/api/market';

export default function Home() {
  const { setRegime, annotation } = useRegime();
  const activeSymbol = annotation?.long_sym || 'TQQQ';

  return (
    <main className="flex min-h-screen flex-col pt-20 pb-12 px-4 relative">
      {/* Header */}
      <div className="z-10 w-full max-w-7xl mx-auto flex items-center justify-between font-mono text-sm mb-6">
        <StatusIndicator />
        <p className="hidden lg:block text-xs opacity-50">RegimeFlex v2.0 // Professional Trading Terminal</p>
      </div>

      {/* Main Content Grid */}
      <div className="w-full max-w-7xl mx-auto">
        {/* Top Row: Chart + Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Main Chart - spans 2 columns */}
          <div className="lg:col-span-2">
            <PriceChart symbol={activeSymbol} backendUrl={BACKEND_URL} />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <RegimePanel />
            <PortfolioCard backendUrl={BACKEND_URL} />
          </div>
        </div>

        {/* Middle Row: Indicators + Market Context */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
          <div className="lg:col-span-3">
            <IndicatorPanels symbol={activeSymbol} backendUrl={BACKEND_URL} />
          </div>
          <div className="lg:col-span-1">
            <MarketContext backendUrl={BACKEND_URL} />
          </div>
        </div>

        {/* Bottom Row: Positions Table */}
        <PositionsTable backendUrl={BACKEND_URL} />
      </div>

      {/* Dev Controls - Hidden by default */}
      <div className="fixed bottom-4 right-4 flex gap-2 opacity-10 hover:opacity-100 transition-opacity z-50">
        <button onClick={() => setRegime('BULL')} className="px-2 py-1 text-xs bg-emerald-900 rounded hover:bg-emerald-800">Bull</button>
        <button onClick={() => setRegime('NEUTRAL')} className="px-2 py-1 text-xs bg-slate-900 rounded hover:bg-slate-800">Neut</button>
        <button onClick={() => setRegime('BEAR')} className="px-2 py-1 text-xs bg-red-900 rounded hover:bg-red-800">Bear</button>
      </div>
    </main>
  );
}
