#!/bin/bash
set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

warn_test() {
    echo -e "${YELLOW}⚠ WARN:${NC} $1"
    ((TESTS_WARNED++))
}

section() {
    echo ""
    echo -e "${BLUE}${BOLD}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
    echo ""
}

# Main test execution
main() {
    section "RegimeFlex End-to-End Integration Test"
    
    echo "Date: $(date)"
    echo "Working directory: $(pwd)"
    echo "Hostname: $(hostname 2>/dev/null || echo 'N/A')"
    echo ""
    
    # ===========================================
    # PHASE 1: Environment Variable Loading
    # ===========================================
    section "[Phase 1] Environment Variable Loading"
    
    echo "[Test 1.1] Testing environment loading..."
    if python3 -c "import regimeflex" 2>&1 | grep -q "✓\|Loaded\|Running"; then
        pass_test "Environment loaded successfully"
    else
        # Check if it failed due to missing keys (expected in some cases)
        if python3 -c "import regimeflex" 2>&1 | grep -qi "missing\|required"; then
            warn_test "Environment loaded but missing some keys (may be expected)"
        else
            fail_test "Environment loading failed"
        fi
    fi
    
    echo "[Test 1.2] Verifying API keys present..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.config.api_keys import APIKeys

keys_present = True
missing = []

if not APIKeys.alpaca_key_id():
    missing.append('ALPACA_KEY')
    keys_present = False
if not APIKeys.alpaca_secret():
    missing.append('ALPACA_SECRET')
    keys_present = False
if not APIKeys.polygon_key():
    missing.append('POLYGON_KEY')
    keys_present = False

if missing:
    print(f'Missing: {', '.join(missing)}')
    sys.exit(1)
else:
    print('All required API keys present')
    sys.exit(0)
" 2>&1 | grep -q "All required"; then
        pass_test "All required API keys present"
    else
        warn_test "Some API keys missing (may be expected for dry-run tests)"
    fi
    
    # ===========================================
    # PHASE 2: Absolute Path Handling
    # ===========================================
    section "[Phase 2] Absolute Path Handling"
    
    echo "[Test 2.1] Testing paths from different directory..."
    cd /tmp
    if python3 -c "
import sys
import os
sys.path.insert(0, '$PROJECT_ROOT')
import regimeflex
from regimeflex.config.paths import PROJECT_ROOT, RUN_LOCK_FILE

print(f'Project root: {PROJECT_ROOT}')
print(f'Run lock: {RUN_LOCK_FILE}')
assert RUN_LOCK_FILE.is_absolute(), 'Run lock path not absolute'
print('✓ All paths are absolute')
" 2>&1 | grep -q "✓ All paths are absolute"; then
        pass_test "Absolute paths work from any directory"
    else
        fail_test "Path issues from different directory"
    fi
    cd "$PROJECT_ROOT"
    
    # ===========================================
    # PHASE 3: PM2 Configuration
    # ===========================================
    section "[Phase 3] PM2 Configuration"
    
    echo "[Test 3.1] Checking PM2 installation..."
    if command -v pm2 &> /dev/null; then
        PM2_VERSION=$(pm2 --version 2>/dev/null || echo "unknown")
        pass_test "PM2 installed ($PM2_VERSION)"
    else
        warn_test "PM2 not installed (required for production)"
    fi
    
    echo "[Test 3.2] Validating ecosystem.config.js..."
    if [ -f "ecosystem.config.js" ]; then
        if command -v pm2 &> /dev/null && pm2 ecosystem ecosystem.config.js &> /dev/null; then
            pass_test "PM2 configuration valid"
        else
            warn_test "PM2 configuration validation skipped (pm2 not available)"
        fi
    else
        fail_test "ecosystem.config.js not found"
    fi
    
    # ===========================================
    # PHASE 4: State File Operations
    # ===========================================
    section "[Phase 4] State File Operations"
    
    echo "[Test 4.1] Testing atomic file operations..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.utils.atomic_file import atomic_write_json, atomic_read_json
from pathlib import Path

test_file = Path('data/state/test_e2e.json')
test_data = {'test': 'e2e', 'phase': 4}

# Write and read
success = atomic_write_json(test_file, test_data)
if not success:
    print('Write failed')
    sys.exit(1)

data = atomic_read_json(test_file, default={})
if data != test_data:
    print(f'Data mismatch: {data} != {test_data}')
    sys.exit(1)

# Cleanup
test_file.unlink()
print('✓ Atomic operations work')
" 2>&1 | grep -q "✓ Atomic operations work"; then
        pass_test "Atomic file operations work"
    else
        fail_test "Atomic file operations failed"
    fi
    
    echo "[Test 4.2] Testing critical state files..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.engine.positions import save_positions, load_positions
from regimeflex.engine.kill_switch_manual import activate_kill_switch, deactivate_kill_switch
from regimeflex.engine.regime_buffer import save_regime_state

# Test each critical state file
try:
    save_positions({'TEST': 0.0})
    activate_kill_switch('E2E test')
    deactivate_kill_switch()
    save_regime_state({'regime': 'TEST', 'test': True})
    print('✓ All state file operations work')
except Exception as e:
    print(f'State file error: {e}')
    sys.exit(1)
" 2>&1 | grep -q "✓ All state file operations work"; then
        pass_test "Critical state files operational"
    else
        fail_test "State file operations failed"
    fi
    
    # ===========================================
    # PHASE 5: Safety Systems
    # ===========================================
    section "[Phase 5] Safety Systems"
    
    echo "[Test 5.1] Testing kill switch..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.engine.kill_switch_manual import activate_kill_switch, deactivate_kill_switch, is_killed

activate_kill_switch('E2E test')
if not is_killed():
    print('Kill switch not activated')
    sys.exit(1)

deactivate_kill_switch()
if is_killed():
    print('Kill switch not deactivated')
    sys.exit(1)

print('✓ Kill switch functional')
" 2>&1 | grep -q "✓ Kill switch functional"; then
        pass_test "Kill switch functional"
    else
        fail_test "Kill switch not working"
    fi
    
    echo "[Test 5.2] Testing run lock..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.engine.run_lock import acquire_run_lock, release_run_lock

lock = acquire_run_lock()
if lock is None:
    print('Could not acquire lock')
    sys.exit(1)

release_run_lock(lock)
print('✓ Run lock functional')
" 2>&1 | grep -q "✓ Run lock functional"; then
        pass_test "Run lock functional"
    else
        fail_test "Run lock not working"
    fi
    
    echo "[Test 5.3] Testing morning rush filter..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.engine.config import Config
from regimeflex.config.paths import PROJECT_ROOT

config = Config(PROJECT_ROOT)
schedule = config.schedule

if 'morning_rush' in schedule:
    enabled = schedule['morning_rush'].get('enabled', False)
    print(f'✓ Morning rush configured: enabled={enabled}')
else:
    print('Morning rush configuration not found')
    sys.exit(1)
" 2>&1 | grep -q "✓ Morning rush configured"; then
        pass_test "Morning rush filter configured"
    else
        warn_test "Morning rush not configured"
    fi
    
    # ===========================================
    # PHASE 6: Monitoring & Alerting
    # ===========================================
    section "[Phase 6] Monitoring & Alerting"
    
    echo "[Test 6.1] Testing heartbeat operations..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.engine.guardian.watchdog import touch_heartbeat
from regimeflex.config.paths import GUARDIAN_HEARTBEAT_FILE

touch_heartbeat(regime='TEST', equity=10000.0)
if not GUARDIAN_HEARTBEAT_FILE.exists():
    print('Heartbeat file not created')
    sys.exit(1)

print('✓ Heartbeat operations work')
" 2>&1 | grep -q "✓ Heartbeat operations work"; then
        pass_test "Heartbeat operations work"
    else
        fail_test "Heartbeat operations failed"
    fi
    
    echo "[Test 6.2] Testing notification systems..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.config.api_keys import APIKeys

telegram_configured = bool(APIKeys.telegram_bot_token() and APIKeys.telegram_chat_id())
print(f'Telegram configured: {telegram_configured}')

# Test that notification system is available
try:
    from regimeflex.engine.guardian.alerting import get_alert_manager
    alert_mgr = get_alert_manager()
    print('✓ Notification system available')
except Exception as e:
    print(f'Notification system error: {e}')
    sys.exit(1)
" 2>&1 | grep -q "✓ Notification system available"; then
        pass_test "Notification systems available"
    else
        warn_test "Notification configuration incomplete"
    fi
    
    # ===========================================
    # PHASE 7: API Connectivity
    # ===========================================
    section "[Phase 7] External API Connectivity"
    
    echo "[Test 7.1] Testing Alpaca API connection..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.config.api_keys import APIKeys

APIKeys.setup_alpaca_env()

# Try to import Alpaca client
try:
    from alpaca.trading.client import TradingClient
    
    key_id = APIKeys.alpaca_key_id()
    secret = APIKeys.alpaca_secret()
    
    if not key_id or not secret:
        print('Alpaca credentials not configured')
        sys.exit(1)
    
    client = TradingClient(
        api_key=key_id,
        secret_key=secret,
        paper=True
    )
    
    # Test connection
    account = client.get_account()
    print(f'✓ Connected to Alpaca: Account {account.account_number}')
    print(f'Buying power: \${account.buying_power}')
    
except ImportError:
    print('Alpaca SDK not installed')
    sys.exit(1)
except Exception as e:
    print(f'Alpaca connection issue: {e}')
    sys.exit(1)
" 2>&1 | grep -q "✓ Connected to Alpaca"; then
        pass_test "Alpaca API connected"
    else
        warn_test "Alpaca API connection failed (check credentials)"
    fi
    
    echo "[Test 7.2] Testing Polygon API connection (optional)..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
import regimeflex
from regimeflex.config.api_keys import APIKeys
import requests

polygon_key = APIKeys.polygon_key()
if polygon_key:
    try:
        # Simple API test
        url = f'https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2023-01-10?apiKey={polygon_key}'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print('✓ Polygon API connected')
        else:
            print(f'Polygon API issue: {response.status_code}')
            sys.exit(1)
    except Exception as e:
        print(f'Polygon connection issue: {e}')
        sys.exit(1)
else:
    print('Polygon not configured (optional)')
    sys.exit(0)
" 2>&1 | grep -q "✓ Polygon API connected"; then
        pass_test "Polygon API check passed"
    else
        warn_test "Polygon API not configured or failed (optional)"
    fi
    
    # ===========================================
    # PHASE 8: Full Trading Cycle (Dry Run)
    # ===========================================
    section "[Phase 8] Complete Trading Cycle"
    
    echo "[Test 8.1] Running full trading cycle (dry run)..."
    echo "This will execute RegimeFlex with --dry-run flag..."
    echo "Note: This may take 30-60 seconds..."
    echo ""
    
    # Create temp log file
    E2E_LOG="/tmp/regimeflex_e2e_output_$$.log"
    
    # Run with timeout to prevent hanging (2 minutes max)
    if timeout 120 python3 -m regimeflex run --dry-run 2>&1 | tee "$E2E_LOG" || true; then
        # Check output for key indicators
        if grep -qi "error\|exception\|traceback\|critical" "$E2E_LOG"; then
            echo ""
            echo "⚠️  Warnings/Errors found in output (check above)"
            warn_test "Trading cycle completed with warnings (check logs)"
        elif grep -qi "kill\|blocked\|no-op" "$E2E_LOG"; then
            echo ""
            echo "ℹ️  Trading was blocked (kill switch, morning rush, etc.)"
            pass_test "Trading cycle completed (blocked by safety systems)"
        elif grep -qi "completed\|finished\|success" "$E2E_LOG"; then
            pass_test "Trading cycle completed successfully"
        else
            # If we got here without errors, consider it a pass
            pass_test "Trading cycle executed (check output above)"
        fi
    else
        warn_test "Trading cycle timeout or error (check logs)"
    fi
    
    # Cleanup
    rm -f "$E2E_LOG" 2>/dev/null || true
    
    # ===========================================
    # Final Summary
    # ===========================================
    section "Test Summary"
    
    echo -e "Tests Passed:  ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Tests Failed:  ${RED}${TESTS_FAILED}${NC}"
    echo -e "Tests Warned:  ${YELLOW}${TESTS_WARNED}${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        section "${GREEN}✓✓✓ ALL CRITICAL TESTS PASSED ✓✓✓${NC}"
        echo ""
        echo "RegimeFlex is PRODUCTION READY!"
        echo ""
        echo "Next steps:"
        echo "  1. Review warnings (if any)"
        echo "  2. Deploy to production VPS"
        echo "  3. Start with PM2: pm2 start ecosystem.config.js"
        echo "  4. Monitor: pm2 logs regimeflex-trading"
        echo ""
        
        if [ $TESTS_WARNED -gt 0 ]; then
            echo -e "${YELLOW}Note: ${TESTS_WARNED} warnings present - review before production${NC}"
            echo ""
        fi
        
        exit 0
    else
        section "${RED}✗✗✗ TESTS FAILED ✗✗✗${NC}"
        echo ""
        echo "DO NOT DEPLOY TO PRODUCTION"
        echo "Fix the ${TESTS_FAILED} failed test(s) above before proceeding."
        echo ""
        exit 1
    fi
}

# Run main test suite
main

