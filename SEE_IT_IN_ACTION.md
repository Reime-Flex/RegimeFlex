# See RegimeFlex in Action! 🚀

## Quick Start - See It Running

### Option 1: Interactive Demo Script (Recommended)

```bash
chmod +x demo_server.sh
./demo_server.sh
```

This will:
- ✅ Start the HTTP server
- ✅ Test all endpoints automatically
- ✅ Show you the responses
- ✅ Keep server running so you can test more

### Option 2: Manual Start

**Terminal 1 - Start Server:**
```bash
python3 -m regimeflex http
```

You should see:
```
 * Serving Flask app 'run_http_trigger'
 * Debug mode: off
 * Running on http://0.0.0.0:5000
```

**Terminal 2 - Test Endpoints:**
```bash
# Health check
curl http://localhost:5000/health

# System status
curl http://localhost:5000/status | python3 -m json.tool

# Latest replay
curl http://localhost:5000/replay/latest | python3 -m json.tool

# Recent incidents
curl http://localhost:5000/incidents | python3 -m json.tool
```

## What You'll See

### 1. Health Endpoint (`/health`)
```json
{
  "status": "ok",
  "timestamp": "2025-01-XX..."
}
```

### 2. Status Endpoint (`/status`)
```json
{
  "status": "active",
  "timestamp": "2025-01-XX...",
  "kill_switch": false
}
```

### 3. Replay Endpoint (`/replay/latest`)
Shows the latest trading replay data (if available):
```json
{
  "found": true,
  "replay": {
    "model": {
      "bull": true,
      "regime": {...}
    },
    "as_of": "2025-01-XX..."
  }
}
```

### 4. Incidents Endpoint (`/incidents`)
Shows recent system incidents:
```json
{
  "count": 0,
  "items": []
}
```

## Web Frontend (If Available)

If you have the web frontend running:

```bash
# Start Next.js frontend (in web/ directory)
cd web
npm run dev

# Then open: http://localhost:3000
```

The frontend will connect to the Python backend at `http://localhost:5000`.

## Test a Full Trading Cycle (Dry Run)

To see the full system in action (without real trades):

```bash
# Set dry-run mode
export REGIMEFLEX_DRY_RUN=1

# Run daily cycle
python3 -m regimeflex run
```

This will:
- ✅ Load configuration
- ✅ Fetch market data
- ✅ Calculate regime
- ✅ Generate trading signals
- ✅ Create order intents
- ✅ Generate reports

**Note**: This requires config files and may need API keys for full functionality.

## Monitor Server Activity

**View logs in real-time:**
```bash
# If using demo_server.sh, logs are in:
tail -f /tmp/regimeflex_demo.log

# Or if running manually, logs go to stdout
```

**Check server is responding:**
```bash
watch -n 1 'curl -s http://localhost:5000/health'
```

## Stop the Server

**If using demo_server.sh:**
- Press `Ctrl+C`

**If running manually:**
- Press `Ctrl+C` in the terminal running the server
- Or: `pkill -f "regimeflex http"`

## Troubleshooting

### Server won't start?
```bash
# Check if port is in use
lsof -i :5000

# Kill existing process
pkill -f "regimeflex http"

# Try different port
PORT=8080 python3 -m regimeflex http
```

### No response from endpoints?
```bash
# Check server logs
tail -20 /tmp/regimeflex_demo.log

# Verify server is running
ps aux | grep regimeflex
```

### Import errors?
```bash
# Test imports first
python3 -c "from regimeflex.scripts.run_http_trigger import app; print('OK')"
```

## Next Steps

Once you see it working locally:

1. ✅ Verify all endpoints respond
2. ✅ Check logs for errors
3. ✅ Test with web frontend (if available)
4. ✅ Deploy to VPS with PM2

**Enjoy seeing RegimeFlex in action!** 🎉

