import { NextRequest } from 'next/server';

// Railway provides these environment variables:
// - RAILWAY_PUBLIC_DOMAIN (for public-facing services)
// - RAILWAY_SERVICE_URL (for internal service-to-service)
// - Or use service name if in same project
const PYTHON_BACKEND_URL =
    process.env.PYTHON_BACKEND_URL ||           // Custom override
    process.env.RAILWAY_SERVICE_URL ||          // Railway service URL
    process.env.RAILWAY_PUBLIC_DOMAIN ||        // Railway public domain
    'http://localhost:8080';                     // Fallback for local dev

/**
 * SSE (Server-Sent Events) proxy endpoint.
 *
 * Proxies SSE connection from the Python backend to the frontend.
 * Provides real-time updates for:
 * - trade_update: Order fills, cancellations, rejections
 * - position_update: Position changes
 * - regime_update: Regime state changes
 * - connection_status: WebSocket connection status
 */
export async function GET(request: NextRequest) {
    const encoder = new TextEncoder();

    // Create a readable stream for SSE
    const stream = new ReadableStream({
        async start(controller) {
            let backendEventSource: EventSource | null = null;
            let keepAliveInterval: NodeJS.Timeout | null = null;
            let isActive = true;

            // Helper to send SSE data
            const sendEvent = (data: string) => {
                if (!isActive) return;
                try {
                    controller.enqueue(encoder.encode(`data: ${data}\n\n`));
                } catch {
                    // Stream closed
                    isActive = false;
                }
            };

            // Helper to send keepalive
            const sendKeepalive = () => {
                if (!isActive) return;
                try {
                    controller.enqueue(encoder.encode(': keepalive\n\n'));
                } catch {
                    // Stream closed
                    isActive = false;
                }
            };

            // Cleanup function
            const cleanup = () => {
                isActive = false;
                if (keepAliveInterval) {
                    clearInterval(keepAliveInterval);
                    keepAliveInterval = null;
                }
                if (backendEventSource) {
                    backendEventSource.close();
                    backendEventSource = null;
                }
            };

            try {
                // Try to connect to backend SSE
                const backendUrl = `${PYTHON_BACKEND_URL}/events`;

                // Use fetch with streaming for SSE proxy
                const response = await fetch(backendUrl, {
                    headers: {
                        'Accept': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                    },
                    // @ts-expect-error - duplex is valid for streaming
                    duplex: 'half',
                });

                if (!response.ok) {
                    // Backend SSE not available - fall back to keepalive mode
                    console.log('[SSE] Backend not available, entering keepalive mode');

                    // Send initial connection status
                    sendEvent(JSON.stringify({
                        event_type: 'connection_status',
                        data: { status: 'connected', source: 'proxy', mode: 'keepalive' },
                        timestamp: new Date().toISOString(),
                    }));

                    // Send keepalive every 30 seconds
                    keepAliveInterval = setInterval(sendKeepalive, 30000);

                    // Handle client disconnect
                    request.signal.addEventListener('abort', cleanup);
                    return;
                }

                // Stream backend SSE to client
                const reader = response.body?.getReader();
                if (!reader) {
                    throw new Error('No response body');
                }

                // Send keepalive every 30 seconds
                keepAliveInterval = setInterval(sendKeepalive, 30000);

                // Handle client disconnect
                request.signal.addEventListener('abort', cleanup);

                // Read and forward events
                const decoder = new TextDecoder();
                let buffer = '';

                while (isActive) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });

                    // Process complete SSE messages
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // Keep incomplete line in buffer

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            sendEvent(data);
                        } else if (line.startsWith(':')) {
                            // Comment/keepalive - forward as is
                            sendKeepalive();
                        }
                    }
                }
            } catch (error) {
                console.error('[SSE] Connection error:', error);

                // Send error status and enter keepalive mode
                sendEvent(JSON.stringify({
                    event_type: 'connection_status',
                    data: { status: 'error', source: 'proxy', error: String(error) },
                    timestamp: new Date().toISOString(),
                }));

                // Continue with keepalive mode
                if (!keepAliveInterval) {
                    keepAliveInterval = setInterval(sendKeepalive, 30000);
                }

                // Handle client disconnect
                request.signal.addEventListener('abort', cleanup);
            }
        },
    });

    // Return SSE response
    return new Response(stream, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no', // Disable nginx buffering
        },
    });
}

// Disable body parsing for streaming
export const dynamic = 'force-dynamic';
