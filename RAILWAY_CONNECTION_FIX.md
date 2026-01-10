# Railway Connection Issues & Fixes

## 🔴 Problems Identified

### 1. **Server Mismatch**
- **Railway config** (`railway.json`) runs: `scripts/run_http_trigger.py` (Flask app)
- **Frontend expects**: `trigger_server.py` (HTTP server with `/replay/latest` endpoint)
- **Problem**: These are different servers with different endpoints!

### 2. **Missing Endpoints**
- `run_http_trigger.py` only has:
  - `/trigger-daily` ✅
  - `/health` ✅
- **Frontend needs**: `/replay/latest` ❌ (only in `trigger_server.py`)

### 3. **Port Configuration**
- `run_http_trigger.py` uses `PORT` env var ✅ (correct for Railway)
- `trigger_server.py` uses `REGIMEFLEX_TRIGGER_PORT` with default `8080` ❌

### 4. **Frontend Hardcoded URL**
- Frontend API route uses `http://localhost:8080` ❌
- In Railway, services need Railway URLs or service discovery

### 5. **CORS Issues**
- If frontend and backend are separate Railway services, CORS headers needed

---

## ✅ Solutions

### Option A: Use `trigger_server.py` (Recommended)

**Update `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python regimeflex/scripts/trigger_server.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Update `trigger_server.py` to use Railway PORT:**
```python
# In trigger_server.py main() function, change:
port = int(os.environ.get("PORT", os.environ.get("REGIMEFLEX_TRIGGER_PORT", "8080")))
```

**Add `/replay/latest` endpoint to `run_http_trigger.py` (if keeping Flask):**
```python
@app.route("/replay/latest", methods=["GET"])
def replay_latest():
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # Find latest replay file
        replay_dir = Path("replays")
        if not replay_dir.exists():
            return jsonify({"found": False}), 404
        
        replay_files = sorted(replay_dir.glob("replay_*.json"), reverse=True)
        if not replay_files:
            return jsonify({"found": False}), 404
        
        latest_file = replay_files[0]
        with open(latest_file, 'r') as f:
            replay_data = json.load(f)
        
        return jsonify({
            "found": True,
            "replay": replay_data
        }), 200
    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500
```

### Option B: Add Missing Endpoints to `run_http_trigger.py`

Add these endpoints to `run_http_trigger.py`:

```python
@app.route("/replay/latest", methods=["GET"])
def replay_latest():
    """Return latest replay pack for frontend."""
    try:
        from pathlib import Path
        import json
        
        # Find latest replay file
        replay_dir = Path("replays")
        if not replay_dir.exists():
            return jsonify({"found": False}), 404
        
        replay_files = sorted(replay_dir.glob("replay_*.json"), reverse=True)
        if not replay_files:
            return jsonify({"found": False}), 404
        
        latest_file = replay_files[0]
        with open(latest_file, 'r') as f:
            replay_data = json.load(f)
        
        return jsonify({
            "found": True,
            "replay": replay_data
        }), 200
    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    """Return system status."""
    try:
        from pathlib import Path
        import json
        
        # Read status from state files or generate
        status_data = {
            "status": "active",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(status_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/incidents", methods=["GET"])
def incidents():
    """Return recent incidents."""
    try:
        from pathlib import Path
        import json
        
        incidents_file = Path("logs/incidents.jsonl")
        if not incidents_file.exists():
            return jsonify({"count": 0, "items": []}), 200
        
        # Read last N incidents
        incidents = []
        with open(incidents_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:  # Last 20
                try:
                    incidents.append(json.loads(line))
                except:
                    pass
        
        return jsonify({
            "count": len(incidents),
            "items": incidents
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Fix Frontend Connection

**Update `web/app/api/regime/route.ts`:**

```typescript
import { NextResponse } from 'next/server';

// Railway provides these environment variables:
// - RAILWAY_PUBLIC_DOMAIN (for public-facing services)
// - RAILWAY_SERVICE_URL (for internal service-to-service)
// - Or use service name if in same project

const PYTHON_BACKEND_URL = 
    process.env.PYTHON_BACKEND_URL ||           // Custom override
    process.env.RAILWAY_SERVICE_URL ||          // Railway service URL
    process.env.RAILWAY_PUBLIC_DOMAIN ||        // Railway public domain
    'http://localhost:5000';                     // Fallback (Flask default)

export async function GET() {
    try {
        // Fetch latest replay from Python backend
        const res = await fetch(
            `${PYTHON_BACKEND_URL}/replay/latest`,
            { 
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                // Add timeout for Railway
                signal: AbortSignal.timeout(5000)
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
            { 
                found: false, 
                error: 'Backend connection failed',
                backend_url: PYTHON_BACKEND_URL  // Debug info
            },
            { status: 503 }
        );
    }
}
```

### Add CORS Headers (if separate services)

**In `run_http_trigger.py`:**
```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (or configure specific origins)
```

**Add to `requirements.txt`:**
```
flask-cors>=4.0.0
```

---

## 🚀 Railway Environment Variables

Set these in Railway dashboard:

### Backend Service:
```
PORT=5000  # Railway will set this automatically, but you can override
REGIMEFLEX_TRIGGER_TOKEN=your_secret_token
```

### Frontend Service:
```
PYTHON_BACKEND_URL=https://your-backend-service.railway.app
# OR if same project:
PYTHON_BACKEND_URL=http://backend-service-name:5000
```

---

## 📋 Quick Fix Checklist

- [ ] Update `railway.json` to use correct server script
- [ ] Add `/replay/latest` endpoint to Flask app (or switch to trigger_server.py)
- [ ] Update frontend API route to use Railway URLs
- [ ] Add CORS headers if services are separate
- [ ] Set Railway environment variables
- [ ] Test connection in Railway logs

---

## 🔍 Debugging in Railway

1. **Check logs**: Railway dashboard → Service → Logs
2. **Test endpoints**: Use Railway's public domain URL
3. **Check environment**: Railway dashboard → Variables
4. **Verify ports**: Railway sets `PORT` automatically

---

## 🎯 Recommended Approach

**Use `trigger_server.py`** because it already has all endpoints:
- `/status`
- `/replay/latest`
- `/incidents`
- `/health`
- `/run`

Just update the port configuration and Railway start command.

