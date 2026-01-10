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

export async function GET() {
    try {
        // Fetch latest replay from Python backend
        // Create AbortController for timeout (more compatible than AbortSignal.timeout)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const res = await fetch(
            `${PYTHON_BACKEND_URL}/replay/latest`,
            { 
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal
            }
        );
        
        clearTimeout(timeoutId);
        
        if (!res.ok) {
            throw new Error(`Backend returned ${res.status}`);
        }
        
        const data = await res.json();
        
        // Extract regime from replay data
        if (data.found && data.replay?.model) {
            const model = data.replay.model;
            const isBull = model.bull ?? model.regime?.bull ?? false;
            
            return NextResponse.json({
                found: true,
                replay: {
                    model: {
                        bull: isBull,
                        regime: { bull: isBull }
                    },
                    as_of: data.replay.as_of || new Date().toISOString()
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
        
        // Return mock data as fallback (for development/testing)
        // In production, you might want to return an error instead
        const mockData = {
            found: false,
            error: 'Backend connection failed',
            backend_url: PYTHON_BACKEND_URL,
            // Fallback mock data
            replay: {
                model: {
                    bull: false,
                    regime: { bull: false }
                },
                as_of: new Date().toISOString()
            }
        };
        
        return NextResponse.json(mockData, { status: 503 });
    }
}
