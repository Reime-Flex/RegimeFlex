'use client';

import React from 'react';
import { useRegime } from '../context/RegimeContext';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, MinusCircle, Wallet, Activity, DollarSign } from 'lucide-react';

export const DashboardHero = () => {
    const { regime, annotation, prices, positionState, asOf, isConnected } = useRegime();

    const getHeroContent = () => {
        const longSym = annotation?.long_sym || 'TQQQ';
        const shortSym = annotation?.short_sym || 'SQQQ';

        switch (regime) {
            case 'BULL':
                return {
                    title: "Aggressive Growth Protocol Active",
                    narrative: `Long ${longSym}. The trend is healthy, and the system is capturing the swing.`,
                    icon: <TrendingUp className="w-8 h-8 text-emerald-400" />,
                    accent: "border-emerald-500/30 bg-emerald-900/20 text-emerald-100",
                    activeSym: longSym
                };
            case 'BEAR':
                return {
                    title: "Defensive Hedge Active",
                    narrative: `Market breakdown detected. Switched to ${shortSym} to capitalize on downside volatility.`,
                    icon: <TrendingDown className="w-8 h-8 text-red-400" />,
                    accent: "border-red-500/30 bg-red-900/20 text-red-100",
                    activeSym: shortSym
                };
            case 'NEUTRAL':
            default:
                return {
                    title: "Capital Preservation Mode",
                    narrative: "Uncertainty detected in the mid-term trend. Preserving capital until a clear direction emerges.",
                    icon: <MinusCircle className="w-8 h-8 text-slate-400" />,
                    accent: "border-slate-500/30 bg-slate-800/20 text-slate-100",
                    activeSym: null
                };
        }
    };

    const content = getHeroContent();
    const qqqPrice = prices?.QQQ;
    const activePrice = content.activeSym ? prices?.[content.activeSym] : null;

    const formatPrice = (price: number | undefined | null) => {
        if (price === undefined || price === null) return '—';
        return `$${price.toFixed(2)}`;
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '—';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="w-full max-w-5xl mx-auto mt-8 px-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                key={regime}
                transition={{ duration: 0.5 }}
                className={`glass-panel rounded-2xl p-8 border ${content.accent} backdrop-blur-xl relative overflow-hidden`}
            >
                <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                    <div className={`p-4 rounded-xl ${content.accent} backdrop-blur-md shadow-inner`}>
                        {content.icon}
                    </div>

                    <div className="flex-1">
                        <h2 className="text-sm uppercase tracking-widest opacity-70 font-mono mb-2">Status At-A-Glance</h2>
                        <h1 className="text-3xl font-bold mb-3 tracking-tight">{content.title}</h1>
                        <p className="text-xl md:text-2xl opacity-90 leading-relaxed font-light">
                            &ldquo;{content.narrative}&rdquo;
                        </p>
                    </div>
                </div>

                {/* Decorative background element */}
                <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-white/5 rounded-full blur-3xl -z-10 pointer-events-none"></div>
            </motion.div>

            {/* Quick Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                {/* QQQ Price */}
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-4">
                    <div className="p-2 bg-white/5 rounded-lg"><DollarSign className="w-5 h-5 opacity-70" /></div>
                    <div>
                        <div className="text-xs uppercase opacity-50">QQQ Index</div>
                        <div className="text-lg font-mono font-bold">
                            {formatPrice(qqqPrice)}
                        </div>
                    </div>
                </div>

                {/* Active Position */}
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-4">
                    <div className="p-2 bg-white/5 rounded-lg"><Activity className="w-5 h-5 opacity-70" /></div>
                    <div>
                        <div className="text-xs uppercase opacity-50">Active Instrument</div>
                        <div className="text-lg font-mono font-bold">
                            {content.activeSym || 'CASH'}
                            {activePrice && <span className="text-xs opacity-50 font-normal ml-2">{formatPrice(activePrice)}</span>}
                        </div>
                    </div>
                </div>

                {/* Positions / Data Date */}
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-4">
                    <div className="p-2 bg-white/5 rounded-lg"><Wallet className="w-5 h-5 opacity-70" /></div>
                    <div>
                        <div className="text-xs uppercase opacity-50">
                            {isConnected && positionState ? 'Open Positions' : 'Data As Of'}
                        </div>
                        <div className="text-lg font-mono font-bold">
                            {isConnected && positionState ? (
                                <>
                                    {positionState.positionCount}
                                    <span className="text-xs opacity-50 font-normal ml-2">
                                        {positionState.hasPositions ? 'active' : 'none'}
                                    </span>
                                </>
                            ) : (
                                formatDate(asOf)
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* No-Op Reason Banner */}
            {annotation?.no_op && annotation.no_op_reason && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-4 p-4 rounded-xl border border-amber-500/30 bg-amber-900/20 text-amber-100"
                >
                    <div className="text-xs uppercase opacity-70 mb-1">System Note</div>
                    <div className="text-sm">{annotation.no_op_reason}</div>
                </motion.div>
            )}
        </div>
    );
};
