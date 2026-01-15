'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Globe, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

interface QuoteData {
    symbol: string;
    last: number;
    change: number;
    change_pct: number;
    prev_close: number;
    volume?: number;
}

interface MarketContextProps {
    backendUrl: string;
}

const MARKET_SYMBOLS = ['SPY', 'QQQ', 'UVXY'];

export const MarketContext: React.FC<MarketContextProps> = ({ backendUrl }) => {
    const [quotes, setQuotes] = useState<Record<string, QuoteData>>({});
    const [isLoading, setIsLoading] = useState(true);

    const fetchQuotes = useCallback(async () => {
        try {
            const response = await fetch(`${backendUrl}/quotes?symbols=${MARKET_SYMBOLS.join(',')}`);
            if (!response.ok) return;
            const data = await response.json();
            if (!data.error) {
                setQuotes(data);
            }
        } catch (error) {
            console.error('Error fetching market quotes:', error);
        } finally {
            setIsLoading(false);
        }
    }, [backendUrl]);

    useEffect(() => {
        fetchQuotes();
        const interval = setInterval(fetchQuotes, 15000); // Update every 15 seconds
        return () => clearInterval(interval);
    }, [fetchQuotes]);

    const formatPrice = (value: number | null | undefined) => {
        if (value === null || value === undefined) return '—';
        return `$${value.toFixed(2)}`;
    };

    const formatChange = (change: number | null | undefined, changePct: number | null | undefined) => {
        if (change === null || change === undefined) return '—';
        const sign = change >= 0 ? '+' : '';
        return `${sign}${change.toFixed(2)} (${sign}${changePct?.toFixed(2)}%)`;
    };

    if (isLoading) {
        return (
            <div className="glass-panel rounded-xl border border-white/10 p-4 animate-pulse">
                <div className="h-24 bg-white/5 rounded" />
            </div>
        );
    }

    const getSymbolConfig = (symbol: string) => {
        switch (symbol) {
            case 'SPY':
                return { label: 'S&P 500', icon: <Globe className="w-4 h-4" /> };
            case 'QQQ':
                return { label: 'NASDAQ 100', icon: <TrendingUp className="w-4 h-4" /> };
            case 'UVXY':
                return { label: 'Volatility (UVXY)', icon: <AlertTriangle className="w-4 h-4" /> };
            default:
                return { label: symbol, icon: <Globe className="w-4 h-4" /> };
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel rounded-xl border border-white/10 overflow-hidden"
        >
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                <Globe className="w-4 h-4 text-white/50" />
                <span className="text-xs uppercase tracking-wider text-white/50">Market Context</span>
            </div>

            {/* Market data grid */}
            <div className="divide-y divide-white/5">
                {MARKET_SYMBOLS.map((symbol, index) => {
                    const quote = quotes[symbol];
                    const config = getSymbolConfig(symbol);
                    const isPositive = quote?.change >= 0;
                    const isVIX = symbol === 'UVXY';

                    return (
                        <motion.div
                            key={symbol}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${
                                    isVIX
                                        ? 'bg-amber-500/10 text-amber-400'
                                        : 'bg-white/5 text-white/50'
                                }`}>
                                    {config.icon}
                                </div>
                                <div>
                                    <div className="font-mono font-medium">{symbol}</div>
                                    <div className="text-xs text-white/40">{config.label}</div>
                                </div>
                            </div>

                            <div className="text-right">
                                <div className="font-mono font-bold">
                                    {formatPrice(quote?.last)}
                                </div>
                                <div className={`text-xs font-mono ${
                                    isVIX
                                        ? (isPositive ? 'text-red-400' : 'text-emerald-400')
                                        : (isPositive ? 'text-emerald-400' : 'text-red-400')
                                }`}>
                                    {quote && (
                                        <span className="flex items-center gap-1 justify-end">
                                            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                            {formatChange(quote.change, quote.change_pct)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </motion.div>
    );
};
