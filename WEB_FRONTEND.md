# RegimeFlex Web Frontend

## 🎨 What the Webpage Looks Like

The RegimeFlex web frontend is a **modern, dark-themed dashboard** built with Next.js and React. Here's what users see:

### Visual Design

- **Dark Theme**: Deep slate background (`#0f172a`) with glassmorphism effects
- **Regime-Based Colors**:
  - **Bull Regime**: Emerald/Green gradient (`#064e3b` → `#022c22`)
  - **Bear Regime**: Ruby/Red gradient (`#7f1d1d` → `#450a0a`)
  - **Neutral Regime**: Slate/Gray gradient (`#334155` → `#1e293b`)
- **Animated Background**: Smooth gradient transitions that change based on regime
- **Glass Panels**: Frosted glass effect with backdrop blur

### Main Components

#### 1. **Status Indicator** (Top Left)
- Connection status dot (green = connected, red = disconnected, yellow = connecting)
- "Live Connected" badge when active
- Last updated timestamp

#### 2. **Dashboard Hero** (Center)
Large status card showing:
- **Regime Title**: 
  - Bull: "Aggressive Growth Protocol Active"
  - Bear: "Defensive Hedge Active"
  - Neutral: "Capital Preservation Mode"
- **Narrative**: Explains current strategy
  - Bull: "We are currently Long TQQQ. The trend is healthy..."
  - Bear: "Market breakdown detected. Switched to SQQQ..."
  - Neutral: "Uncertainty detected. Moving to Cash..."
- **Icon**: TrendingUp (bull), TrendingDown (bear), or MinusCircle (neutral)

#### 3. **Quick Stats Row** (Below Hero)
Three stat cards:
- **Trend Strength**: "84% Strong" (placeholder)
- **Risk Level**: "Low Vol: 1.2%" (placeholder)
- **Logic Visualization**: "Pending..." (placeholder)

#### 4. **Dev Controls** (Bottom Right)
Temporary buttons to manually switch regimes (for testing UI)

---

## 🔌 Backend Connection Status

### Current State: **NOT CONNECTED** ⚠️

The frontend is currently using **mock data** and is **NOT connected** to the Python backend.

#### Frontend API Route (`web/app/api/regime/route.ts`)
```typescript
// Currently returns MOCK data
const mockData = {
    found: true,
    replay: {
        model: {
            bull: true  // Hardcoded
        }
    }
};
```

#### Python Backend Available
The Python backend has these endpoints on port **8080**:
- `/status` - System status (read-only)
- `/replay/latest` - Latest replay pack (read-only)
- `/incidents` - Recent incidents (read-only)
- `/health` - Health check
- `/run` - Execute trading cycle (requires token)

---

## 🔧 How to Connect Frontend to Backend

### Option 1: Connect via Next.js API Route (Recommended)

Update `web/app/api/regime/route.ts` to call the Python backend:

```typescript
import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8080';
const BACKEND_TOKEN = process.env.REGIMEFLEX_TRIGGER_TOKEN || '';

export async function GET() {
    try {
        // Fetch latest replay from Python backend
        const res = await fetch(
            `${PYTHON_BACKEND_URL}/replay/latest?mode=summary&token=${BACKEND_TOKEN}`,
            { 
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            }
        );
        
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
        
        // No replay found
        return NextResponse.json({
            found: false,
            replay: null
        });
        
    } catch (error) {
        console.error('Failed to fetch from Python backend:', error);
        return NextResponse.json(
            { found: false, error: 'Backend connection failed' },
            { status: 503 }
        );
    }
}
```

### Option 2: Direct File System Access

Read directly from replay files (if Next.js has file system access):

```typescript
import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
    try {
        // Path to replay files (adjust based on your deployment)
        const replayDir = path.join(process.cwd(), '../../replays');
        const files = fs.readdirSync(replayDir)
            .filter(f => f.startsWith('replay_') && f.endsWith('.json'))
            .sort()
            .reverse();
        
        if (files.length === 0) {
            return NextResponse.json({ found: false });
        }
        
        const latestFile = path.join(replayDir, files[0]);
        const replayData = JSON.parse(fs.readFileSync(latestFile, 'utf-8'));
        
        // Extract regime
        const isBull = replayData.model?.bull ?? replayData.model?.regime?.bull ?? false;
        
        return NextResponse.json({
            found: true,
            replay: {
                model: { bull: isBull, regime: { bull: isBull } },
                as_of: replayData.as_of
            }
        });
    } catch (error) {
        return NextResponse.json({ found: false, error: String(error) }, { status: 500 });
    }
}
```

---

## 🚀 Running the Web Frontend

### Development Mode

```bash
cd web
npm install  # First time only
npm run dev
```

Then visit: **http://localhost:3000**

### Production Build

```bash
cd web
npm run build
npm start
```

---

## 📋 Environment Variables Needed

Create `web/.env.local`:

```bash
# Python Backend URL
PYTHON_BACKEND_URL=http://localhost:8080

# Backend API Token (if required)
REGIMEFLEX_TRIGGER_TOKEN=your_token_here
```

---

## 🎯 Next Steps to Complete Integration

1. **Update API Route**: Replace mock data with real backend calls
2. **Add More Endpoints**: 
   - `/api/status` - System status
   - `/api/health` - Health check
   - `/api/incidents` - Recent incidents
3. **Real-Time Updates**: Use WebSockets or polling for live regime updates
4. **Add More Stats**: Connect trend strength, risk level from actual data
5. **Position Display**: Show current positions and P&L
6. **Order History**: Display recent trades and fills

---

## 🎨 UI Preview

The dashboard features:
- **Smooth animations** when regime changes (Framer Motion)
- **Responsive design** (mobile-friendly)
- **Real-time status** updates every 10 seconds
- **Professional aesthetic** with glassmorphism and gradients

---

**Current Status**: Frontend is functional but uses mock data. Backend integration is the next step.

