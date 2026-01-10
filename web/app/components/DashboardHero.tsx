'use client';

import React from 'react';
import { useRegime } from '../context/RegimeContext';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, MinusCircle, ShieldAlert, Activity } from 'lucide-react';

export const DashboardHero = () => {
    const { regime } = useRegime();

    const getHeroContent = () => {
        switch (regime) {
            case 'BULL':
                return {
                    title: "Aggressive Growth Protocol Active",
                    narrative: "We are currently Long TQQQ. The trend is healthy, and the robot is ignoring minor noise to capture the 4-day swing.",
                    icon: <TrendingUp className="w-8 h-8 text-emerald-400" />,
                    accent: "border-emerald-500/30 bg-emerald-900/20 text-emerald-100"
                };
            case 'BEAR':
                return {
                    title: "Defensive Hedge Active",
                    narrative: "Market breakdown detected. Switched to SQQQ to capitalize on downside volatility while protecting principal.",
                    icon: <TrendingDown className="w-8 h-8 text-red-400" />,
                    accent: "border-red-500/30 bg-red-900/20 text-red-100"
                };
            case 'NEUTRAL':
            default:
                return {
                    title: "Capital Preservation Mode",
                    narrative: "Uncertainty detected in the mid-term trend. Moving to Cash (BIL) to preserve capital until a clear direction emerges.",
                    icon: <MinusCircle className="w-8 h-8 text-slate-400" />,
                    accent: "border-slate-500/30 bg-slate-800/20 text-slate-100"
                };
        }
    };

    const content = getHeroContent();

    return (
        <div className="w-full max-w-5xl mx-auto mt-8 px-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                key={regime} // Re-animate on regime change
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
                            "{content.narrative}"
                        </p>
                    </div>
                </div>

                {/* Decorative background element */}
                <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-white/5 rounded-full blur-3xl -z-10 pointer-events-none"></div>
            </motion.div>

            {/* Quick Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-4">
                    <div className="p-2 bg-white/5 rounded-lg"><Activity className="w-5 h-5 opacity-70" /></div>
                    <div>
                        <div className="text-xs uppercase opacity-50">Trend Strength</div>
                        <div className="text-lg font-mono font-bold">84% <span className="text-xs opacity-50 font-normal">Strong</span></div>
                    </div>
                </div>
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center gap-4">
                    <div className="p-2 bg-white/5 rounded-lg"><ShieldAlert className="w-5 h-5 opacity-70" /></div>
                    <div>
                        <div className="text-xs uppercase opacity-50">Risk Level</div>
                        <div className="text-lg font-mono font-bold">Low <span className="text-xs opacity-50 font-normal">Vol: 1.2%</span></div>
                    </div>
                </div>

                {/* Placeholder for the Logic Visualization later */}
                <div className="glass-panel p-4 rounded-xl border border-white/5 flex items-center justify-between opacity-50 border-dashed">
                    <span className="text-sm">Logic Visualization Pending...</span>
                </div>
            </div>
        </div>
    );
};
