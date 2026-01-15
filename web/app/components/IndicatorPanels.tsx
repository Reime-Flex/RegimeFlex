'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, BarChart3 } from 'lucide-react';

interface Indicators {
    rsi: number | null;
    macd: number | null;
    macd_signal: number | null;
    macd_histogram: number | null;
    bb_upper: number | null;
    bb_middle: number | null;
    bb_lower: number | null;
    atr: number | null;
    sma_20: number | null;
    sma_50: number | null;
    sma_200: number | null;
}

interface IndicatorPanelsProps {
    symbol: string;
    backendUrl: string;
}

export const IndicatorPanels: React.FC<IndicatorPanelsProps> = ({ symbol, backendUrl }) => {
    const [indicators, setIndicators] = useState<Indicators | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchIndicators = useCallback(async () => {
        try {
            const response = await fetch(`${backendUrl}/indicators?symbol=${symbol}&tf=1Day&limit=200`);
            if (!response.ok) return;
            const data = await response.json();
            setIndicators(data.indicators);
        } catch (error) {
            console.error('Error fetching indicators:', error);
        } finally {
            setIsLoading(false);
        }
    }, [symbol, backendUrl]);

    useEffect(() => {
        fetchIndicators();
        const interval = setInterval(fetchIndicators, 60000); // Update every minute
        return () => clearInterval(interval);
    }, [fetchIndicators]);

    const formatValue = (value: number | null | undefined, decimals = 2) => {
        if (value === null || value === undefined) return '—';
        return value.toFixed(decimals);
    };

    const getRSIColor = (rsi: number | null) => {
        if (rsi === null) return 'text-white/50';
        if (rsi >= 70) return 'text-red-400';
        if (rsi <= 30) return 'text-emerald-400';
        return 'text-white';
    };

    const getRSILabel = (rsi: number | null) => {
        if (rsi === null) return '';
        if (rsi >= 70) return 'Overbought';
        if (rsi <= 30) return 'Oversold';
        return 'Neutral';
    };

    const getMACDColor = (macd: number | null) => {
        if (macd === null) return 'text-white/50';
        return macd >= 0 ? 'text-emerald-400' : 'text-red-400';
    };

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="glass-panel rounded-xl border border-white/10 p-4 animate-pulse">
                        <div className="h-16 bg-white/5 rounded" />
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* RSI Panel */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-panel rounded-xl border border-white/10 p-4"
            >
                <div className="flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-white/50" />
                    <span className="text-xs uppercase tracking-wider text-white/50">RSI (14)</span>
                </div>
                <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-mono font-bold ${getRSIColor(indicators?.rsi ?? null)}`}>
                        {formatValue(indicators?.rsi)}
                    </span>
                    <span className={`text-xs ${getRSIColor(indicators?.rsi ?? null)}`}>
                        {getRSILabel(indicators?.rsi ?? null)}
                    </span>
                </div>
                {/* RSI Visual Bar */}
                <div className="mt-3 h-2 bg-white/10 rounded-full overflow-hidden relative">
                    <div className="absolute inset-0 flex">
                        <div className="w-[30%] bg-emerald-500/30" />
                        <div className="w-[40%] bg-white/10" />
                        <div className="w-[30%] bg-red-500/30" />
                    </div>
                    {indicators?.rsi && (
                        <div
                            className="absolute top-0 bottom-0 w-1 bg-white rounded-full transform -translate-x-1/2"
                            style={{ left: `${indicators.rsi}%` }}
                        />
                    )}
                </div>
                <div className="flex justify-between text-xs text-white/30 mt-1">
                    <span>30</span>
                    <span>50</span>
                    <span>70</span>
                </div>
            </motion.div>

            {/* MACD Panel */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-panel rounded-xl border border-white/10 p-4"
            >
                <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-white/50" />
                    <span className="text-xs uppercase tracking-wider text-white/50">MACD (12,26,9)</span>
                </div>
                <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-mono font-bold ${getMACDColor(indicators?.macd ?? null)}`}>
                        {formatValue(indicators?.macd)}
                    </span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                    <div>
                        <span className="text-white/40">Signal: </span>
                        <span className="font-mono">{formatValue(indicators?.macd_signal)}</span>
                    </div>
                    <div>
                        <span className="text-white/40">Hist: </span>
                        <span className={`font-mono ${getMACDColor(indicators?.macd_histogram ?? null)}`}>
                            {formatValue(indicators?.macd_histogram)}
                        </span>
                    </div>
                </div>
                {/* MACD Histogram Visual */}
                {indicators?.macd_histogram !== null && indicators?.macd_histogram !== undefined && (
                    <div className="mt-3 flex items-center justify-center">
                        <div className="w-full h-6 relative">
                            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/20" />
                            <div
                                className={`absolute top-1 bottom-1 ${
                                    indicators.macd_histogram >= 0 ? 'left-1/2 bg-emerald-500/50' : 'right-1/2 bg-red-500/50'
                                }`}
                                style={{
                                    width: `${Math.min(Math.abs(indicators.macd_histogram) * 10, 50)}%`,
                                }}
                            />
                        </div>
                    </div>
                )}
            </motion.div>

            {/* ATR Panel */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-panel rounded-xl border border-white/10 p-4"
            >
                <div className="flex items-center gap-2 mb-3">
                    <BarChart3 className="w-4 h-4 text-white/50" />
                    <span className="text-xs uppercase tracking-wider text-white/50">Volatility & MAs</span>
                </div>
                <div className="flex items-baseline gap-2 mb-3">
                    <span className="text-xs text-white/40">ATR (14):</span>
                    <span className="text-2xl font-mono font-bold">{formatValue(indicators?.atr)}</span>
                </div>
                <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                        <span className="text-white/40">SMA 20:</span>
                        <span className="font-mono">${formatValue(indicators?.sma_20)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-white/40">SMA 50:</span>
                        <span className="font-mono">${formatValue(indicators?.sma_50)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-white/40">SMA 200:</span>
                        <span className="font-mono">${formatValue(indicators?.sma_200)}</span>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};
