'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Briefcase, TrendingUp, TrendingDown } from 'lucide-react';

interface Position {
    symbol: string;
    qty: number;
    side: 'long' | 'short';
    avg_entry: number;
    current_price: number;
    market_value: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
    cost_basis?: number;
}

interface PositionsTableProps {
    backendUrl: string;
}

export const PositionsTable: React.FC<PositionsTableProps> = ({ backendUrl }) => {
    const [positions, setPositions] = useState<Position[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchPositions = useCallback(async () => {
        try {
            const response = await fetch(`${backendUrl}/positions`);
            if (!response.ok) return;
            const data = await response.json();
            if (!data.error) {
                setPositions(data.positions || []);
            }
        } catch (error) {
            console.error('Error fetching positions:', error);
        } finally {
            setIsLoading(false);
        }
    }, [backendUrl]);

    useEffect(() => {
        fetchPositions();
        const interval = setInterval(fetchPositions, 15000); // Update every 15 seconds
        return () => clearInterval(interval);
    }, [fetchPositions]);

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    };

    const formatPercent = (value: number) => {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    };

    if (isLoading) {
        return (
            <div className="glass-panel rounded-xl border border-white/10 p-6 animate-pulse">
                <div className="h-32 bg-white/5 rounded" />
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel rounded-xl border border-white/10 overflow-hidden"
        >
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-white/50" />
                    <span className="text-sm uppercase tracking-wider text-white/50">Open Positions</span>
                </div>
                <span className="text-sm text-white/40">{positions.length} position{positions.length !== 1 ? 's' : ''}</span>
            </div>

            {/* Table */}
            {positions.length === 0 ? (
                <div className="p-8 text-center text-white/40">
                    <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>No open positions</p>
                    <p className="text-sm mt-1">The system is currently in cash</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-xs text-white/40 uppercase tracking-wider">
                                <th className="text-left px-6 py-3">Symbol</th>
                                <th className="text-right px-6 py-3">Side</th>
                                <th className="text-right px-6 py-3">Qty</th>
                                <th className="text-right px-6 py-3">Entry</th>
                                <th className="text-right px-6 py-3">Current</th>
                                <th className="text-right px-6 py-3">Value</th>
                                <th className="text-right px-6 py-3">P&L</th>
                            </tr>
                        </thead>
                        <tbody>
                            {positions.map((position, index) => {
                                const isProfitable = position.unrealized_pnl >= 0;
                                return (
                                    <motion.tr
                                        key={position.symbol}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="border-t border-white/5 hover:bg-white/5 transition-colors"
                                    >
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono font-bold">{position.symbol}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                                                position.side === 'long'
                                                    ? 'bg-emerald-500/20 text-emerald-400'
                                                    : 'bg-red-500/20 text-red-400'
                                            }`}>
                                                {position.side === 'long' ? (
                                                    <TrendingUp className="w-3 h-3" />
                                                ) : (
                                                    <TrendingDown className="w-3 h-3" />
                                                )}
                                                {position.side.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono">{position.qty}</td>
                                        <td className="px-6 py-4 text-right font-mono text-white/70">
                                            {formatCurrency(position.avg_entry)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono">
                                            {formatCurrency(position.current_price)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono">
                                            {formatCurrency(position.market_value)}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className={`font-mono ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                                                <div>{formatCurrency(position.unrealized_pnl)}</div>
                                                <div className="text-xs opacity-70">
                                                    {formatPercent(position.unrealized_pnl_pct)}
                                                </div>
                                            </div>
                                        </td>
                                    </motion.tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </motion.div>
    );
};
