'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * SSE Event Types
 */
export interface TradeUpdateEvent {
    event: string;  // "fill" | "partial_fill" | "canceled" | "rejected" | "new"
    order_id: string;
    symbol: string;
    qty: number;
    filled_qty: number;
    price: number;
    timestamp: string;
    side: string;
    order_type: string;
}

export interface PositionUpdateEvent {
    positions: Record<string, number>;
}

export interface RegimeUpdateEvent {
    regime: string;
    confidence: number;
}

export interface ConnectionStatusEvent {
    status: 'connected' | 'disconnected';
    source: string;
    reason?: string;
}

export type SSEEventType = 'trade_update' | 'position_update' | 'regime_update' | 'connection_status';

export interface SSEEvent {
    event_type: SSEEventType;
    data: TradeUpdateEvent | PositionUpdateEvent | RegimeUpdateEvent | ConnectionStatusEvent;
    timestamp: string;
}

export interface UseSSEOptions {
    /** URL of the SSE endpoint */
    url?: string;
    /** Whether to enable SSE connection */
    enabled?: boolean;
    /** Delay in ms before reconnecting after disconnect */
    reconnectDelay?: number;
    /** Maximum reconnect attempts before giving up */
    maxReconnectAttempts?: number;
    /** Callback for trade updates */
    onTradeUpdate?: (event: TradeUpdateEvent) => void;
    /** Callback for position updates */
    onPositionUpdate?: (event: PositionUpdateEvent) => void;
    /** Callback for regime updates */
    onRegimeUpdate?: (event: RegimeUpdateEvent) => void;
    /** Callback for connection status changes */
    onConnectionStatus?: (event: ConnectionStatusEvent) => void;
    /** Callback for any event */
    onEvent?: (event: SSEEvent) => void;
    /** Callback when SSE connection opens */
    onOpen?: () => void;
    /** Callback when SSE connection errors */
    onError?: (error: Event) => void;
}

export interface UseSSEReturn {
    /** Whether SSE is currently connected */
    isConnected: boolean;
    /** Current connection state */
    connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
    /** Number of reconnect attempts */
    reconnectAttempts: number;
    /** Last received event */
    lastEvent: SSEEvent | null;
    /** Last error message */
    error: string | null;
    /** Manually disconnect */
    disconnect: () => void;
    /** Manually reconnect */
    reconnect: () => void;
}

/**
 * React hook for Server-Sent Events (SSE) connection to RegimeFlex backend.
 *
 * Features:
 * - Auto-reconnect on disconnect
 * - Typed event handlers
 * - Connection state tracking
 * - Manual disconnect/reconnect
 *
 * @example
 * ```tsx
 * const { isConnected, lastEvent } = useSSE({
 *     onTradeUpdate: (event) => console.log('Trade:', event),
 *     onRegimeUpdate: (event) => setRegime(event.regime),
 * });
 * ```
 */
export function useSSE(options: UseSSEOptions = {}): UseSSEReturn {
    const {
        url = '/api/events',
        enabled = true,
        reconnectDelay = 5000,
        maxReconnectAttempts = 10,
        onTradeUpdate,
        onPositionUpdate,
        onRegimeUpdate,
        onConnectionStatus,
        onEvent,
        onOpen,
        onError,
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
    const [error, setError] = useState<string | null>(null);

    const eventSourceRef = useRef<EventSource | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const mountedRef = useRef(true);
    const connectRef = useRef<() => void>(() => {});

    // Cleanup function
    const cleanup = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    }, []);

    // Disconnect function
    const disconnect = useCallback(() => {
        cleanup();
        setIsConnected(false);
        setConnectionState('disconnected');
        setReconnectAttempts(0);
    }, [cleanup]);

    // Connect function - uses ref for self-reference to avoid circular dependency
    const connect = useCallback(() => {
        if (!enabled || !mountedRef.current) return;

        cleanup();
        setConnectionState('connecting');
        setError(null);

        try {
            const eventSource = new EventSource(url);
            eventSourceRef.current = eventSource;

            eventSource.onopen = () => {
                if (!mountedRef.current) return;
                setIsConnected(true);
                setConnectionState('connected');
                setReconnectAttempts(0);
                setError(null);
                onOpen?.();
            };

            eventSource.onmessage = (event) => {
                if (!mountedRef.current) return;

                try {
                    const parsed: SSEEvent = JSON.parse(event.data);
                    setLastEvent(parsed);
                    onEvent?.(parsed);

                    // Route to specific handlers
                    switch (parsed.event_type) {
                        case 'trade_update':
                            onTradeUpdate?.(parsed.data as TradeUpdateEvent);
                            break;
                        case 'position_update':
                            onPositionUpdate?.(parsed.data as PositionUpdateEvent);
                            break;
                        case 'regime_update':
                            onRegimeUpdate?.(parsed.data as RegimeUpdateEvent);
                            break;
                        case 'connection_status':
                            onConnectionStatus?.(parsed.data as ConnectionStatusEvent);
                            break;
                    }
                } catch (parseError) {
                    console.error('[SSE] Failed to parse event:', parseError, event.data);
                }
            };

            eventSource.onerror = (errorEvent) => {
                if (!mountedRef.current) return;

                setIsConnected(false);
                setConnectionState('error');
                onError?.(errorEvent);

                // Check if we should reconnect
                if (eventSource.readyState === EventSource.CLOSED) {
                    setReconnectAttempts((prev) => {
                        const newAttempts = prev + 1;
                        if (newAttempts <= maxReconnectAttempts) {
                            setError(`Connection lost. Reconnecting (${newAttempts}/${maxReconnectAttempts})...`);
                            reconnectTimeoutRef.current = setTimeout(() => {
                                if (mountedRef.current) {
                                    connectRef.current();
                                }
                            }, reconnectDelay);
                        } else {
                            setError('Connection failed. Max reconnect attempts reached.');
                            setConnectionState('disconnected');
                        }
                        return newAttempts;
                    });
                }
            };
        } catch (err) {
            setConnectionState('error');
            setError(err instanceof Error ? err.message : 'Failed to create EventSource');
        }
    }, [
        enabled,
        url,
        reconnectDelay,
        maxReconnectAttempts,
        cleanup,
        onOpen,
        onError,
        onEvent,
        onTradeUpdate,
        onPositionUpdate,
        onRegimeUpdate,
        onConnectionStatus,
    ]);

    // Update ref when connect changes
    useEffect(() => {
        connectRef.current = connect;
    }, [connect]);

    // Reconnect function (resets attempts)
    const reconnect = useCallback(() => {
        setReconnectAttempts(0);
        connectRef.current();
    }, []);

    // Effect to manage connection lifecycle
    useEffect(() => {
        mountedRef.current = true;

        if (enabled) {
            connectRef.current();
        }

        return () => {
            mountedRef.current = false;
            cleanup();
        };
    }, [enabled, cleanup]);

    return {
        isConnected,
        connectionState,
        reconnectAttempts,
        lastEvent,
        error,
        disconnect,
        reconnect,
    };
}

export default useSSE;
