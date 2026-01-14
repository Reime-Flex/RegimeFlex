import { NextResponse } from 'next/server';

// Railway provides these environment variables:
// - RAILWAY_PUBLIC_DOMAIN (for public-facing services)
// - RAILWAY_SERVICE_URL (for internal service-to-service)
// - Or use service name if in same project
const PYTHON_BACKEND_URL =
    process.env.PYTHON_BACKEND_URL ||           // Custom override
    process.env.RAILWAY_SERVICE_URL ||          // Railway service URL
    process.env.RAILWAY_PUBLIC_DOMAIN ||        // Railway public domain
    'http://localhost:8080';                     // Fallback for local dev

interface ReplayData {
    annotation?: {
        summary?: string;
        intents?: number;
        no_op?: boolean;
        no_op_reason?: string;
        long_sym?: string;
        short_sym?: string;
    };
    as_of?: string;
    ts_utc?: string;
    symbols?: Record<string, { last_price?: number }>;
    state?: {
        positions_before?: Record<string, unknown>;
        positions_after?: Record<string, unknown>;
        intents?: unknown[];
    };
    guards?: {
        session?: string;
        no_op?: boolean;
        no_op_reason?: string;
    };
    metrics?: {
        signal_stability?: Record<string, unknown>;
        regime_accuracy?: Record<string, unknown>;
    };
    provenance?: {
        model?: {
            bull?: boolean;
            regime?: { bull?: boolean };
        };
    };
}

export async function GET() {
    try {
        // Fetch latest replay from Python backend
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const res = await fetch(
            `${PYTHON_BACKEND_URL}/replay/latest`,
            {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                cache: 'no-store'
            }
        );

        clearTimeout(timeoutId);

        const data = await res.json();

        // 404 means no replay files - not an error, just no data yet
        if (res.status === 404 || !data.found) {
            return NextResponse.json({
                found: false,
                replay: null,
                message: data.error || 'No trading data available yet'
            });
        }

        if (!res.ok) {
            throw new Error(`Backend returned ${res.status}`);
        }

        // Extract regime from replay data
        if (data.found && data.replay) {
            const replay = data.replay as ReplayData;

            // Look for bull flag in provenance.model or fallback locations
            const model = replay.provenance?.model;
            let isBull: boolean | undefined = undefined;

            if (model) {
                if (typeof model.bull === 'boolean') isBull = model.bull;
                else if (model.regime && typeof model.regime.bull === 'boolean') isBull = model.regime.bull;
            }

            // Extract additional useful data
            const annotation = replay.annotation || {};
            const symbols = replay.symbols || {};
            const longSym = annotation.long_sym || 'TQQQ';
            const shortSym = annotation.short_sym || 'SQQQ';

            return NextResponse.json({
                found: true,
                replay: {
                    model: {
                        bull: isBull ?? false,
                        regime: { bull: isBull ?? false }
                    },
                    as_of: replay.as_of || new Date().toISOString(),
                    ts_utc: replay.ts_utc,
                    annotation: {
                        summary: annotation.summary,
                        intents: annotation.intents || 0,
                        no_op: annotation.no_op ?? false,
                        no_op_reason: annotation.no_op_reason || '',
                        long_sym: longSym,
                        short_sym: shortSym
                    },
                    prices: {
                        [longSym]: symbols[longSym]?.last_price,
                        [shortSym]: symbols[shortSym]?.last_price,
                        QQQ: symbols['QQQ']?.last_price
                    },
                    state: {
                        hasPositions: Object.keys(replay.state?.positions_after || {}).length > 0,
                        positionCount: Object.keys(replay.state?.positions_after || {}).length
                    }
                }
            });
        }

        // No replay found - return neutral state
        return NextResponse.json({
            found: false,
            replay: null
        });

    } catch (error) {
        console.error('Failed to fetch from Python backend:', error);
        console.error('Backend URL:', PYTHON_BACKEND_URL);

        // Return error state for frontend to handle
        return NextResponse.json({
            found: false,
            error: 'Backend connection failed',
            backend_url: PYTHON_BACKEND_URL,
            replay: null
        }, { status: 503 });
    }
}
