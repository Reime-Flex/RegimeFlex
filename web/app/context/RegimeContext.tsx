'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useSSE, RegimeUpdateEvent, PositionUpdateEvent, TradeUpdateEvent } from '../hooks/useSSE';
import type { ConnectionState } from '../components/ConnectionStatus';

export type RegimeType = 'BULL' | 'BEAR' | 'NEUTRAL';

interface ReplayAnnotation {
    summary?: string;
    intents: number;
    no_op: boolean;
    no_op_reason: string;
    long_sym: string;
    short_sym: string;
}

interface ReplayPrices {
    [symbol: string]: number | undefined;
}

interface ReplayState {
    hasPositions: boolean;
    positionCount: number;
}

interface TradeEvent {
    event: string;
    symbol: string;
    qty: number;
    price: number;
    timestamp: string;
    side: string;
}

interface RegimeContextType {
    regime: RegimeType;
    setRegime: (regime: RegimeType) => void;
    isLoading: boolean;
    isConnected: boolean;
    lastUpdated: Date | null;
    error: string | null;
    // Extended data from replay
    annotation: ReplayAnnotation | null;
    prices: ReplayPrices | null;
    positionState: ReplayState | null;
    asOf: string | null;
    // SSE connection state
    connectionState: ConnectionState;
    isLive: boolean;
    // Recent trade events from SSE
    recentTrades: TradeEvent[];
}

const defaultAnnotation: ReplayAnnotation = {
    intents: 0,
    no_op: false,
    no_op_reason: '',
    long_sym: 'TQQQ',
    short_sym: 'SQQQ'
};

const RegimeContext = createContext<RegimeContextType | undefined>(undefined);

// Polling interval when SSE is disconnected (fallback)
const FALLBACK_POLL_INTERVAL = 10000;
// Polling interval when SSE is connected (less frequent, for data sync)
const CONNECTED_POLL_INTERVAL = 60000;

export const RegimeProvider = ({ children }: { children: ReactNode }) => {
    const [regime, setRegimeState] = useState<RegimeType>('NEUTRAL');
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [annotation, setAnnotation] = useState<ReplayAnnotation | null>(null);
    const [prices, setPrices] = useState<ReplayPrices | null>(null);
    const [positionState, setPositionState] = useState<ReplayState | null>(null);
    const [asOf, setAsOf] = useState<string | null>(null);
    const [recentTrades, setRecentTrades] = useState<TradeEvent[]>([]);

    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // Wrapper to allow manual updates (e.g. for testing UI)
    const setRegime = (r: RegimeType) => {
        setRegimeState(r);
        setLastUpdated(new Date());
    };

    // SSE event handlers
    const handleRegimeUpdate = useCallback((event: RegimeUpdateEvent) => {
        const regimeStr = event.regime.toUpperCase();
        if (regimeStr === 'BULL' || regimeStr === 'BEAR' || regimeStr === 'NEUTRAL') {
            setRegimeState(regimeStr as RegimeType);
            setLastUpdated(new Date());
        }
    }, []);

    const handlePositionUpdate = useCallback((event: PositionUpdateEvent) => {
        // Update position state when we receive real-time position updates
        const positions = event.positions;
        const count = Object.keys(positions).length;
        setPositionState({
            hasPositions: count > 0,
            positionCount: count,
        });
        setLastUpdated(new Date());
    }, []);

    const handleTradeUpdate = useCallback((event: TradeUpdateEvent) => {
        // Add to recent trades (keep last 10)
        const tradeEvent: TradeEvent = {
            event: event.event,
            symbol: event.symbol,
            qty: event.qty,
            price: event.price,
            timestamp: event.timestamp,
            side: event.side,
        };
        setRecentTrades(prev => [tradeEvent, ...prev].slice(0, 10));
        setLastUpdated(new Date());
    }, []);

    // Initialize SSE connection
    const {
        isConnected: sseConnected,
        connectionState,
        error: sseError,
    } = useSSE({
        url: '/api/events',
        enabled: true,
        reconnectDelay: 5000,
        maxReconnectAttempts: 10,
        onRegimeUpdate: handleRegimeUpdate,
        onPositionUpdate: handlePositionUpdate,
        onTradeUpdate: handleTradeUpdate,
        onOpen: () => {
            setIsConnected(true);
            setError(null);
        },
        onError: () => {
            // SSE error - will fall back to polling
            setError(sseError || 'SSE connection failed');
        },
    });

    // Fetch regime data (for initial load and polling fallback)
    const fetchRegime = useCallback(async () => {
        try {
            const res = await fetch('/api/regime');
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || `Error ${res.status}`);
            }

            setIsConnected(true);

            if (data.found && data.replay) {
                const replay = data.replay;

                // Determine regime from model
                const model = replay.model || {};
                let isBull: boolean | undefined = undefined;

                if (typeof model.bull === 'boolean') isBull = model.bull;
                else if (model.regime && typeof model.regime.bull === 'boolean') isBull = model.regime.bull;

                if (isBull !== undefined) {
                    setRegimeState(isBull ? 'BULL' : 'BEAR');
                } else {
                    setRegimeState('NEUTRAL');
                }

                // Set extended data
                if (replay.annotation) {
                    setAnnotation({
                        ...defaultAnnotation,
                        ...replay.annotation
                    });
                }

                if (replay.prices) {
                    setPrices(replay.prices);
                }

                if (replay.state) {
                    setPositionState(replay.state);
                }

                if (replay.as_of) {
                    setAsOf(replay.as_of);
                    setLastUpdated(new Date(replay.ts_utc || replay.as_of));
                } else {
                    setLastUpdated(new Date());
                }
            } else {
                // No replay found - stay neutral
                setIsConnected(true);
                setAnnotation(null);
                setPrices(null);
                setPositionState(null);
                setAsOf(null);
            }

            // Clear error on successful fetch
            if (!sseConnected) {
                setError(null);
            }
        } catch (err: unknown) {
            console.error('Failed to fetch regime:', err);
            if (!sseConnected) {
                setIsConnected(false);
                const errorMessage = err instanceof Error ? err.message : String(err);
                setError(errorMessage || 'Connection failed');
            }
        } finally {
            setIsLoading(false);
        }
    }, [sseConnected]);

    // Initial fetch on mount
    useEffect(() => {
        fetchRegime();
    }, [fetchRegime]);

    // Polling with adaptive interval based on SSE connection
    useEffect(() => {
        // Clear existing interval
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
        }

        // Set polling interval based on SSE status
        const interval = sseConnected ? CONNECTED_POLL_INTERVAL : FALLBACK_POLL_INTERVAL;
        pollIntervalRef.current = setInterval(fetchRegime, interval);

        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, [sseConnected, fetchRegime]);

    return (
        <RegimeContext.Provider value={{
            regime,
            setRegime,
            isLoading,
            isConnected,
            lastUpdated,
            error,
            annotation,
            prices,
            positionState,
            asOf,
            connectionState,
            isLive: sseConnected,
            recentTrades,
        }}>
            {children}
        </RegimeContext.Provider>
    );
};

export const useRegime = () => {
    const context = useContext(RegimeContext);
    if (context === undefined) {
        throw new Error('useRegime must be used within a RegimeProvider');
    }
    return context;
};
