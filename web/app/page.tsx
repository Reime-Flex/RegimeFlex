'use client';

import { StatusIndicator } from './components/StatusIndicator';
import { DashboardHero } from './components/DashboardHero';
import { useRegime } from './context/RegimeContext';

export default function Home() {
  const { setRegime } = useRegime();

  return (
    <main className="flex min-h-screen flex-col items-center pt-24 pb-12 px-4 relative">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex mb-8">
        <StatusIndicator />
        <p className="hidden lg:block text-xs opacity-50">RegimeFlex v2.0 // Command Center</p>
      </div>

      <DashboardHero />

      {/* Dev Controls - Temporary */}
      <div className="fixed bottom-4 right-4 flex gap-2 opacity-20 hover:opacity-100 transition-opacity">
        <button onClick={() => setRegime('BULL')} className="px-2 py-1 text-xs bg-emerald-900 rounded">Bull</button>
        <button onClick={() => setRegime('NEUTRAL')} className="px-2 py-1 text-xs bg-slate-900 rounded">Neut</button>
        <button onClick={() => setRegime('BEAR')} className="px-2 py-1 text-xs bg-red-900 rounded">Bear</button>
      </div>
    </main >
  );
}
