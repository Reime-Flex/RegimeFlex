# Quick Pre-Deployment Test Guide

## 🚀 Fastest Way to Test (5 minutes)

### Step 1: Test Imports (30 seconds)

```bash
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))

from regimeflex.engine.runner import run_daily_offline, main
from regimeflex.scripts.run_http_trigger import app, main
from regimeflex.engine.identity import RegimeFlexIdentity

print('✅ All imports work!')
"
```

**Expected**: Should print "✅ All imports work!" with no errors.

### Step 2: Test Module Execution (30 seconds)

```bash
python3 -m regimeflex --help
```

**Expected**: Should show help text with commands (run, http, health).

### Step 3: Test HTTP Server Startup (1 minute)

```bash
# Start server in background
python3 -m regimeflex http &
SERVER_PID=$!

# Wait 2 seconds
sleep 2

# Test health endpoint
curl http://localhost:5000/health

# Stop server
kill $SERVER_PID
```

**Expected**: Should return `{"status": "ok", "timestamp": "..."}`

### Step 4: Test PM2 Command (30 seconds)

```bash
# Test the exact command PM2 will use
python3 -m regimeflex http &
sleep 2
curl http://localhost:5000/status
pkill -f "regimeflex http"
```

**Expected**: Should return status JSON without errors.

### Step 5: Verify Config Files (30 seconds)

```bash
ls -la regimeflex/config/*.yaml | head -5
```

**Expected**: Should show config files (run.yaml, risk.yaml, etc.)

## ✅ All Tests Pass? You're Ready!

If all 5 steps pass, your app is ready for VPS deployment.

## 🐛 If Something Fails

### Import Errors
- **Check**: Are you in the repo root directory?
- **Fix**: `cd /path/to/RegimeFlex` then retry

### Module Not Found
- **Check**: Is `regimeflex/__init__.py` present?
- **Fix**: Ensure you're in the correct directory

### HTTP Server Won't Start
- **Check**: Is port 5000 already in use?
- **Fix**: `lsof -i :5000` then kill the process or change PORT

### Config Missing
- **Check**: Do config files exist?
- **Fix**: Ensure `regimeflex/config/` directory has YAML files

## 📋 Pre-Deploy Checklist

- [ ] Step 1: Imports work ✅
- [ ] Step 2: Module execution works ✅
- [ ] Step 3: HTTP server starts ✅
- [ ] Step 4: PM2 command works ✅
- [ ] Step 5: Config files exist ✅

**All checked? Push to VPS!**

