'use client';

import React from 'react';

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

interface ConnectionStatusProps {
    /** Current connection state */
    state: ConnectionState;
    /** Last updated timestamp */
    lastUpdated?: Date | null;
    /** Whether using SSE or polling */
    isLive?: boolean;
    /** Error message if any */
    error?: string | null;
    /** Whether to show compact version */
    compact?: boolean;
    /** Additional CSS classes */
    className?: string;
}

/**
 * Connection status indicator component.
 * Shows real-time connection status with visual feedback.
 */
export function ConnectionStatus({
    state,
    lastUpdated,
    isLive = false,
    error,
    compact = false,
    className = '',
}: ConnectionStatusProps) {
    // Status colors and labels
    const statusConfig: Record<ConnectionState, { color: string; bgColor: string; label: string; pulse: boolean }> = {
        connecting: {
            color: 'text-yellow-400',
            bgColor: 'bg-yellow-400',
            label: 'Connecting',
            pulse: true,
        },
        connected: {
            color: 'text-green-400',
            bgColor: 'bg-green-400',
            label: isLive ? 'Live' : 'Connected',
            pulse: isLive,
        },
        disconnected: {
            color: 'text-gray-400',
            bgColor: 'bg-gray-400',
            label: 'Disconnected',
            pulse: false,
        },
        error: {
            color: 'text-red-400',
            bgColor: 'bg-red-400',
            label: 'Error',
            pulse: false,
        },
    };

    const config = statusConfig[state];

    // Format last updated time
    const formatTime = (date: Date) => {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);

        if (seconds < 10) return 'just now';
        if (seconds < 60) return `${seconds}s ago`;
        if (minutes < 60) return `${minutes}m ago`;
        return date.toLocaleTimeString();
    };

    if (compact) {
        return (
            <div className={`flex items-center gap-1.5 ${className}`}>
                <div className="relative">
                    <div className={`w-2 h-2 rounded-full ${config.bgColor}`} />
                    {config.pulse && (
                        <div className={`absolute inset-0 w-2 h-2 rounded-full ${config.bgColor} animate-ping opacity-75`} />
                    )}
                </div>
                <span className={`text-xs ${config.color}`}>{config.label}</span>
            </div>
        );
    }

    return (
        <div className={`flex items-center gap-3 ${className}`}>
            {/* Status indicator */}
            <div className="flex items-center gap-2">
                <div className="relative">
                    <div className={`w-2.5 h-2.5 rounded-full ${config.bgColor}`} />
                    {config.pulse && (
                        <div className={`absolute inset-0 w-2.5 h-2.5 rounded-full ${config.bgColor} animate-ping opacity-75`} />
                    )}
                </div>
                <span className={`text-sm font-medium ${config.color}`}>
                    {config.label}
                </span>
            </div>

            {/* Last updated */}
            {lastUpdated && state === 'connected' && (
                <span className="text-xs text-gray-500">
                    Updated {formatTime(lastUpdated)}
                </span>
            )}

            {/* Error message */}
            {error && state === 'error' && (
                <span className="text-xs text-red-400 truncate max-w-[200px]" title={error}>
                    {error}
                </span>
            )}
        </div>
    );
}

/**
 * Compact status dot for use in headers/toolbars
 */
export function StatusDot({
    state,
    className = '',
}: {
    state: ConnectionState;
    className?: string;
}) {
    const colors: Record<ConnectionState, string> = {
        connecting: 'bg-yellow-400',
        connected: 'bg-green-400',
        disconnected: 'bg-gray-400',
        error: 'bg-red-400',
    };

    const shouldPulse = state === 'connecting' || state === 'connected';

    return (
        <div className={`relative ${className}`}>
            <div className={`w-2 h-2 rounded-full ${colors[state]}`} />
            {shouldPulse && (
                <div className={`absolute inset-0 w-2 h-2 rounded-full ${colors[state]} animate-ping opacity-75`} />
            )}
        </div>
    );
}

export default ConnectionStatus;
