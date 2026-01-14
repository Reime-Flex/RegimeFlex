'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

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
}

const defaultAnnotation: ReplayAnnotation = {
    intents: 0,
    no_op: false,
    no_op_reason: '',
    long_sym: 'TQQQ',
    short_sym: 'SQQQ'
};

const RegimeContext = createContext<RegimeContextType | undefined>(undefined);

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

    // Wrapper to allow manual updates (e.g. for testing UI)
    const setRegime = (r: RegimeType) => {
        setRegimeState(r);
        setLastUpdated(new Date());
    };

    useEffect(() => {
        const fetchRegime = async () => {
            try {
                setError(null);
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
            } catch (err: unknown) {
                console.error('Failed to fetch regime:', err);
                setIsConnected(false);
                const errorMessage = err instanceof Error ? err.message : String(err);
                setError(errorMessage || 'Connection failed');
            } finally {
                setIsLoading(false);
            }
        };

        // Initial fetch
        fetchRegime();

        // Poll every 10 seconds
        const interval = setInterval(fetchRegime, 10000);
        return () => clearInterval(interval);
    }, []);

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
            asOf
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
