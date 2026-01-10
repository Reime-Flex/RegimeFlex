# Pre-Deployment Testing Guide

## Quick Test Checklist

Before deploying to VPS, run these tests to ensure everything works:

### 1. Automated Test Script

Run the comprehensive test script:

```bash
chmod +x test_before_deploy.sh
./test_before_deploy.sh
```

This tests:
- ✅ Python environment
- ✅ Package structure
- ✅ Absolute imports
- ✅ Module execution
- ✅ HTTP server startup
- ✅ Configuration files
- ✅ Dependencies
- ✅ PM2 configuration

### 2. Manual Import Tests

Test that all critical imports work:

```bash
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))

# Test critical imports
from regimeflex.engine.runner import run_daily_offline, main
from regimeflex.scripts.run_http_trigger import app, main
from regimeflex.engine.identity import RegimeFlexIdentity

print('✅ All imports work!')
"
```

### 3. Module Execution Tests

Test module execution (how PM2 will run it):

```bash
# Test help command
python3 -m regimeflex --help

# Test engine module
python3 -m regimeflex.engine.runner --help 2>&1 | head -5

# Test HTTP command (will start server - Ctrl+C to stop)
# python3 -m regimeflex http
```

### 4. HTTP Server Test

Test the HTTP server locally:

```bash
# Option 1: Use test script
chmod +x test_http_server.sh
./test_http_server.sh

# Option 2: Manual test
# Terminal 1: Start server
python3 -m regimeflex http

# Terminal 2: Test endpoints
curl http://localhost:5000/health
curl http://localhost:5000/status
curl http://localhost:5000/replay/latest
```

### 5. Dry-Run Execution Test

Test a full dry-run cycle (no real trades):

```bash
# Set dry-run mode
export REGIMEFLEX_DRY_RUN=1

# Run daily cycle (will fail gracefully if config missing, but imports should work)
python3 -m regimeflex run 2>&1 | head -20
```

### 6. PM2 Simulation Test

Simulate how PM2 will run it:

```bash
# Test with PM2 locally (if installed)
pm2 start ecosystem.config.js --env development
pm2 logs regimeflex --lines 50
pm2 stop regimeflex
pm2 delete regimeflex

# Or test the exact command PM2 will use
python3 -m regimeflex http &
sleep 2
curl http://localhost:5000/health
pkill -f "regimeflex http"
```

### 7. Configuration Check

Verify configuration files exist:

```bash
ls -la regimeflex/config/
# Should see: run.yaml, risk.yaml, exposure.yaml, broker.yaml, etc.
```

### 8. Environment Variables Check

Verify environment setup:

```bash
# Check if .env exists
if [ -f .env ]; then
    echo "✅ .env file exists"
    # Don't print contents (contains secrets)
else
    echo "⚠️  .env file missing - create from env.example"
fi

# Check required vars are documented
grep -E "ALPACA_KEY|POLYGON_KEY|TELEGRAM" .env.example 2>/dev/null || echo "Check env.example"
```

## Common Issues and Fixes

### Issue: ImportError

**Symptom**: `ImportError: attempted relative import with no known parent package`

**Fix**: Ensure you're using absolute imports (already done in refactor)

**Test**:
```bash
python3 -c "from regimeflex.engine.runner import main; print('OK')"
```

### Issue: Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'regimeflex'`

**Fix**: Ensure parent directory is in sys.path (path guard in scripts)

**Test**:
```bash
python3 regimeflex/scripts/run_http_trigger.py --help 2>&1 | head -5
```

### Issue: Config Missing

**Symptom**: `Missing config: config/run.yaml`

**Fix**: Ensure config files exist in `regimeflex/config/`

**Test**:
```bash
ls regimeflex/config/*.yaml
```

### Issue: Port Already in Use

**Symptom**: `Address already in use`

**Fix**: Change PORT or kill existing process

**Test**:
```bash
lsof -i :5000  # Check what's using port 5000
```

## Pre-Deployment Checklist

- [ ] Run `./test_before_deploy.sh` - all tests pass
- [ ] Test imports manually - no ImportError
- [ ] Test module execution - `python3 -m regimeflex --help` works
- [ ] Test HTTP server - endpoints respond correctly
- [ ] Verify config files exist - `ls regimeflex/config/`
- [ ] Check environment variables - `.env` configured
- [ ] Test PM2 config - `ecosystem.config.js` uses `-m regimeflex http`
- [ ] Review logs - no errors in test runs

## VPS Deployment Steps

After local testing passes:

1. **Push to Git**:
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **On VPS**:
   ```bash
   cd ~/apps/RegimeFlex
   git pull origin main
   
   # Activate venv
   source .venv312/bin/activate
   
   # Install/update dependencies
   pip install -r requirements.txt
   pip install -e .  # Install package
   
   # Test imports
   python3 -m regimeflex --help
   
   # Start with PM2
   pm2 start ecosystem.config.js
   pm2 logs regimeflex
   ```

3. **Verify on VPS**:
   ```bash
   # Check PM2 status
   pm2 status
   
   # Check logs
   pm2 logs regimeflex --lines 50
   
   # Test endpoints
   curl http://localhost:5000/health
   ```

## Success Criteria

✅ All automated tests pass
✅ No ImportError in any execution method
✅ HTTP server starts and responds
✅ PM2 can start the process
✅ All endpoints return expected status codes

**If all tests pass, you're ready to deploy!**

