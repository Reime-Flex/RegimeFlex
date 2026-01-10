'use client';

import React from 'react';
import { useRegime } from '../context/RegimeContext';

export const StatusIndicator = () => {
    const { isConnected, isLoading, error, lastUpdated } = useRegime();

    if (isLoading && !isConnected) {
        return (
            <div className="flex items-center gap-2 p-4 lg:p-0">
                <div className="h-3 w-3 animate-pulse rounded-full bg-yellow-500"></div>
                <span className="text-sm text-yellow-500">Connecting...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center gap-2 p-4 lg:p-0" title={error}>
                <div className="h-3 w-3 rounded-full bg-red-500"></div>
                <span className="text-sm text-red-500">Disconnected</span>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-4 p-4 lg:p-0">
            <div className="flex items-center gap-2">
                <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                <span className="text-sm text-emerald-500 font-medium">Live Connected</span>
            </div>
            {lastUpdated && (
                <span className="text-xs text-neutral-500">
                    Updated: {lastUpdated.toLocaleTimeString()}
                </span>
            )}
        </div>
    );
};
