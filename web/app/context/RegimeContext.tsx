'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type RegimeType = 'BULL' | 'BEAR' | 'NEUTRAL';

interface RegimeContextType {
    regime: RegimeType;
    setRegime: (regime: RegimeType) => void;
    isLoading: boolean;
    isConnected: boolean;
    lastUpdated: Date | null;
    error: string | null;
}

const RegimeContext = createContext<RegimeContextType | undefined>(undefined);

export const RegimeProvider = ({ children }: { children: ReactNode }) => {
    const [regime, setRegimeState] = useState<RegimeType>('NEUTRAL');
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Wrapper to allow manual updates (e.g. for testing UI)
    const setRegime = (r: RegimeType) => {
        setRegimeState(r);
        // If manually set, we might considered 'lastUpdated' as now
        setLastUpdated(new Date());
    };

    useEffect(() => {
        const fetchRegime = async () => {
            try {
                setError(null);
                // Fetch from our local proxy API
                const res = await fetch('/api/regime');
                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || `Error ${res.status}`);
                }

                setIsConnected(true);

                if (data.found && data.replay) {
                    // Try to locate 'bull' flag in the model data
                    // Structure depends on how 'model' is saved in replay.json
                    // Defensive coding to find 'bull' key
                    const model = data.replay.model || {};
                    let isBull: boolean | undefined = undefined;

                    // Check various likely paths
                    if (typeof model.bull === 'boolean') isBull = model.bull;
                    else if (model.regime && typeof model.regime.bull === 'boolean') isBull = model.regime.bull;
                    else if (model.regime && typeof model.regime === 'boolean') isBull = model.regime; // unlikely but possible

                    if (isBull !== undefined) {
                        setRegimeState(isBull ? 'BULL' : 'BEAR');
                    } else {
                        // Fallback if data found but structure unclear
                        console.warn('Backend data found but could not determine Bull/Bear status:', model);
                        if (regime === 'NEUTRAL') setRegimeState('NEUTRAL'); // Keep neutral if unsure?
                    }

                    // Update timestamp from replay file if available
                    if (data.replay.as_of) {
                        // Parse timestamp (might be ISO string)
                        setLastUpdated(new Date(data.replay.as_of));
                    } else {
                        setLastUpdated(new Date());
                    }
                } else {
                    // No replay found -> System might be idle or fresh
                    // Don't error, just stay Neutral or current state
                    setIsConnected(true); // Connected but no data
                }
            } catch (err: unknown) {
                console.error('Failed to fetch regime:', err);
                // Don't overwrite regime on transient error, just mark connection issue
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
    }, [regime]); // Added regime to dependency array as it's used in strict mode fallback (though minor)

    return (
        <RegimeContext.Provider value={{ regime, setRegime, isLoading, isConnected, lastUpdated, error }}>
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
