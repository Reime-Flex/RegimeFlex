import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND_URL =
    process.env.PYTHON_BACKEND_URL ||
    process.env.RAILWAY_SERVICE_URL ||
    'http://localhost:8080';

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'TQQQ';

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const res = await fetch(
            `${PYTHON_BACKEND_URL}/quote/${symbol}`,
            {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                cache: 'no-store'
            }
        );

        clearTimeout(timeoutId);

        if (!res.ok) {
            throw new Error(`Backend returned ${res.status}`);
        }

        const data = await res.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error('Failed to fetch quote:', error);
        return NextResponse.json(
            { error: 'Failed to fetch quote' },
            { status: 503 }
        );
    }
}
