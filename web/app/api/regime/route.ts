import { NextResponse } from 'next/server';

export async function GET() {
    // In a real scenario, this would read from the Python backend's output file
    // e.g., fs.readFile('/path/to/data/state/latest_replay.json')

    // Mock data for now to satisfy the frontend
    const mockData = {
        found: true,
        replay: {
            model: {
                bull: true, // Simulating a BULL regime
                regime: {
                    bull: true
                }
            },
            as_of: new Date().toISOString()
        }
    };

    return NextResponse.json(mockData);
}
