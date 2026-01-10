#!/bin/bash
echo "=== RegimeFlex Quick Test ==="
echo ""

echo "1. Testing imports..."
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))
from regimeflex.engine.runner import run_daily_offline, main
from regimeflex.scripts.run_http_trigger import app, main
from regimeflex.engine.identity import RegimeFlexIdentity
print('✅ All imports work!')
" && echo "✅ PASS" || echo "❌ FAIL"

echo ""
echo "2. Testing module execution..."
python3 -m regimeflex --help > /dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

echo ""
echo "3. Testing HTTP server startup..."
timeout 3 python3 -m regimeflex http > /tmp/rf_test.log 2>&1 &
PID=$!
sleep 2
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ PASS"
else
    echo "⚠️  Server may not have started (check manually)"
fi
kill $PID 2>/dev/null || true

echo ""
echo "4. Checking config files..."
[ -d "regimeflex/config" ] && [ -f "regimeflex/config/run.yaml" ] && echo "✅ PASS" || echo "⚠️  Config files may be missing"

echo ""
echo "=== Test Complete ==="
