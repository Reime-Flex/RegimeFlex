import { NextResponse } from 'next/server';

export async function GET() {
    return NextResponse.json({ 
        status: 'ok',
        service: 'regimeflex-frontend',
        timestamp: new Date().toISOString()
    });
}

