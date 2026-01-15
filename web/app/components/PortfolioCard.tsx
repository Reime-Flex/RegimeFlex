'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Wallet, TrendingUp, TrendingDown, DollarSign, Percent } from 'lucide-react';

interface Account {
    equity: number;
    cash: number;
    buying_power: number;
    portfolio_value: number;
    last_equity: number;
    day_pnl: number;
    day_pnl_pct: number;
    pattern_day_trader?: boolean;
    trading_blocked?: boolean;
}

interface PortfolioCardProps {
    backendUrl: string;
}

export const PortfolioCard: React.FC<PortfolioCardProps> = ({ backendUrl }) => {
    const [account, setAccount] = useState<Account | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchAccount = useCallback(async () => {
        try {
            const response = await fetch(`${backendUrl}/account`);
            if (!response.ok) return;
            const data = await response.json();
            if (!data.error) {
                setAccount(data);
            }
        } catch (error) {
            console.error('Error fetching account:', error);
        } finally {
            setIsLoading(false);
        }
    }, [backendUrl]);

    useEffect(() => {
        fetchAccount();
        const interval = setInterval(fetchAccount, 30000); // Update every 30 seconds
        return () => clearInterval(interval);
    }, [fetchAccount]);

    const formatCurrency = (value: number | null | undefined) => {
        if (value === null || value === undefined) return '—';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    };

    const formatPercent = (value: number | null | undefined) => {
        if (value === null || value === undefined) return '—';
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    };

    if (isLoading) {
        return (
            <div className="glass-panel rounded-xl border border-white/10 p-6 animate-pulse">
                <div className="h-32 bg-white/5 rounded" />
            </div>
        );
    }

    if (!account) {
        return (
            <div className="glass-panel rounded-xl border border-white/10 p-6">
                <div className="text-center text-white/50">
                    <Wallet className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Unable to load account data</p>
                </div>
            </div>
        );
    }

    const isProfitable = account.day_pnl >= 0;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel rounded-xl border border-white/10 overflow-hidden"
        >
            {/* Header */}
            <div className={`px-6 py-4 border-b border-white/5 ${isProfitable ? 'bg-emerald-900/10' : 'bg-red-900/10'}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Wallet className="w-5 h-5 text-white/50" />
                        <span className="text-sm uppercase tracking-wider text-white/50">Portfolio</span>
                    </div>
                    <div className={`flex items-center gap-1 ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isProfitable ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        <span className="text-sm font-mono">{formatPercent(account.day_pnl_pct)}</span>
                    </div>
                </div>
            </div>

            {/* Main content */}
            <div className="p-6">
                {/* Equity */}
                <div className="mb-6">
                    <div className="text-xs text-white/40 mb-1">Total Equity</div>
                    <div className="text-4xl font-mono font-bold tracking-tight">
                        {formatCurrency(account.equity)}
                    </div>
                    <div className={`text-sm font-mono mt-1 ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                        {isProfitable ? '+' : ''}{formatCurrency(account.day_pnl)} today
                    </div>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white/5 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-white/40 text-xs mb-1">
                            <DollarSign className="w-3 h-3" />
                            Cash
                        </div>
                        <div className="font-mono text-lg">{formatCurrency(account.cash)}</div>
                    </div>
                    <div className="bg-white/5 rounded-lg p-3">
                        <div className="flex items-center gap-1 text-white/40 text-xs mb-1">
                            <Percent className="w-3 h-3" />
                            Buying Power
                        </div>
                        <div className="font-mono text-lg">{formatCurrency(account.buying_power)}</div>
                    </div>
                </div>

                {/* Warnings */}
                {account.trading_blocked && (
                    <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                        Trading is currently blocked
                    </div>
                )}
                {account.pattern_day_trader && (
                    <div className="mt-4 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg text-amber-400 text-sm">
                        PDT flag enabled
                    </div>
                )}
            </div>
        </motion.div>
    );
};
