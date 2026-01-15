'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, MinusCircle, Clock, Activity, Zap } from 'lucide-react';
import { useRegime, RegimeType } from '../context/RegimeContext';

export const RegimePanel: React.FC = () => {
    const { regime, annotation, asOf, isLoading, lastUpdated } = useRegime();

    const getRegimeConfig = (r: RegimeType) => {
        switch (r) {
            case 'BULL':
                return {
                    label: 'BULLISH',
                    description: 'Aggressive Growth Mode',
                    icon: <TrendingUp className="w-6 h-6" />,
                    color: 'emerald',
                    bgGradient: 'from-emerald-900/40 to-emerald-950/20',
                    borderColor: 'border-emerald-500/30',
                    textColor: 'text-emerald-400',
                    ringColor: 'ring-emerald-500/50',
                    activeSym: annotation?.long_sym || 'TQQQ',
                };
            case 'BEAR':
                return {
                    label: 'BEARISH',
                    description: 'Defensive Hedge Mode',
                    icon: <TrendingDown className="w-6 h-6" />,
                    color: 'red',
                    bgGradient: 'from-red-900/40 to-red-950/20',
                    borderColor: 'border-red-500/30',
                    textColor: 'text-red-400',
                    ringColor: 'ring-red-500/50',
                    activeSym: annotation?.short_sym || 'SQQQ',
                };
            default:
                return {
                    label: 'NEUTRAL',
                    description: 'Capital Preservation',
                    icon: <MinusCircle className="w-6 h-6" />,
                    color: 'slate',
                    bgGradient: 'from-slate-800/40 to-slate-900/20',
                    borderColor: 'border-slate-500/30',
                    textColor: 'text-slate-400',
                    ringColor: 'ring-slate-500/50',
                    activeSym: null,
                };
        }
    };

    const config = getRegimeConfig(regime);

    const formatLastUpdate = () => {
        if (!lastUpdated) return '—';
        const now = new Date();
        const diff = Math.floor((now.getTime() - lastUpdated.getTime()) / 1000);

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return lastUpdated.toLocaleDateString();
    };

    const formatAsOf = () => {
        if (!asOf) return '—';
        try {
            const date = new Date(asOf);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return asOf;
        }
    };

    if (isLoading) {
        return (
            <div className="glass-panel rounded-xl border border-white/10 p-6 animate-pulse">
                <div className="h-40 bg-white/5 rounded" />
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`glass-panel rounded-xl border ${config.borderColor} overflow-hidden bg-gradient-to-br ${config.bgGradient}`}
        >
            {/* Status Header */}
            <div className="px-6 py-4 border-b border-white/5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-white/50" />
                        <span className="text-xs uppercase tracking-wider text-white/50">System Regime</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-white/40">
                        <Clock className="w-3 h-3" />
                        <span>{formatLastUpdate()}</span>
                    </div>
                </div>
            </div>

            {/* Main regime display */}
            <div className="p-6">
                <motion.div
                    key={regime}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 200 }}
                    className="flex items-center gap-4 mb-6"
                >
                    <div className={`p-4 rounded-xl ${config.textColor} bg-white/5 ring-2 ${config.ringColor}`}>
                        {config.icon}
                    </div>
                    <div>
                        <div className={`text-2xl font-bold tracking-tight ${config.textColor}`}>
                            {config.label}
                        </div>
                        <div className="text-sm text-white/50">{config.description}</div>
                    </div>
                </motion.div>

                {/* Active instrument */}
                {config.activeSym && (
                    <div className="bg-white/5 rounded-lg p-4 mb-4">
                        <div className="text-xs text-white/40 mb-1">Active Instrument</div>
                        <div className="flex items-center justify-between">
                            <span className={`text-xl font-mono font-bold ${config.textColor}`}>
                                {config.activeSym}
                            </span>
                            <Activity className={`w-5 h-5 ${config.textColor} opacity-50`} />
                        </div>
                    </div>
                )}

                {/* Confidence indicator (visual representation) */}
                <div className="mb-4">
                    <div className="flex items-center justify-between text-xs text-white/40 mb-2">
                        <span>Regime Strength</span>
                        <span>{regime === 'NEUTRAL' ? 'Low' : 'High'}</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: regime === 'NEUTRAL' ? '30%' : '85%' }}
                            transition={{ delay: 0.3, duration: 0.5 }}
                            className={`h-full ${
                                regime === 'BULL'
                                    ? 'bg-emerald-500'
                                    : regime === 'BEAR'
                                    ? 'bg-red-500'
                                    : 'bg-slate-500'
                            }`}
                        />
                    </div>
                </div>

                {/* Data timestamp */}
                <div className="text-xs text-white/30 border-t border-white/5 pt-4 mt-4">
                    <div className="flex justify-between">
                        <span>Data as of:</span>
                        <span className="font-mono">{formatAsOf()}</span>
                    </div>
                    {annotation?.intents !== undefined && (
                        <div className="flex justify-between mt-1">
                            <span>Trade intents:</span>
                            <span className="font-mono">{annotation.intents}</span>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
};
