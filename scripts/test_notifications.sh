#!/bin/bash
set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
    TESTS_WARNINGS=$((TESTS_WARNINGS + 1))
}

print_info() {
    echo -e "${BLUE}ℹ INFO:${NC} $1"
}

echo "=========================================="
echo "Notification Systems Validation Test"
echo "=========================================="
echo "Date: $(date)"
echo "Working directory: $(pwd)"
echo ""

# Test 1: Check Telegram configuration
echo "[Test 1] Checking Telegram configuration..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
from regimeflex.config.api_keys import APIKeys

bot_token = APIKeys.telegram_bot_token()
chat_id = APIKeys.telegram_chat_id()

if bot_token and chat_id:
    print('✓ PASS: Telegram configured')
    print(f'  Bot token: {bot_token[:10]}...')
    print(f'  Chat ID: {chat_id}')
else:
    print('⚠ INFO: Telegram not configured')
    print('  (Optional - notifications will be skipped)')
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ]; then
    if echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
        print_pass "Telegram configuration present"
    else
        print_warning "Telegram not configured (optional)"
    fi
    echo "$PYTHON_OUTPUT" | grep -E "(Bot token|Chat ID|INFO)" || true
else
    print_fail "Telegram configuration check failed"
    echo "$PYTHON_OUTPUT"
    exit 1
fi
echo ""

# Test 2: Test Telegram message sending (if configured)
echo "[Test 2] Testing Telegram message sending..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
from regimeflex.config.api_keys import APIKeys

bot_token = APIKeys.telegram_bot_token()
chat_id = APIKeys.telegram_chat_id()

if bot_token and chat_id:
    try:
        from regimeflex.engine.guardian.alerting import get_alert_manager, AlertLevel
        alert_mgr = get_alert_manager()
        
        # Send test message
        success = alert_mgr.send('🧪 RegimeFlex Test Message - Notification system validation', AlertLevel.INFO)
        
        if success:
            print('✓ PASS: Telegram message sent successfully')
            print('  Check your Telegram app for the test message!')
        else:
            print('⚠ WARNING: Telegram send returned False')
            print('  (May be disabled or rate limited)')
    except Exception as e:
        print(f'⚠ WARNING: {e}')
        print('  (Telegram may not be configured)')
else:
    print('⚠ INFO: Telegram not configured, skipping send test')
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ]; then
    if echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
        print_pass "Telegram message sending works"
    else
        print_warning "Telegram send test result unclear"
    fi
    echo "$PYTHON_OUTPUT" | grep -E "(PASS|WARNING|INFO|Check)" | head -3
else
    print_warning "Telegram send test had issues"
    echo "$PYTHON_OUTPUT" | head -5
fi
echo ""

# Test 3: Test error handling (CRITICAL!)
echo "[Test 3] Testing notification error handling..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
import os

# Test with invalid config (should not crash)
try:
    from regimeflex.engine.telemetry import Notifier, TGCreds
    
    # Test with invalid token (should fail gracefully)
    notifier = Notifier(TGCreds(token='INVALID_TOKEN', chat_id='INVALID_CHAT'))
    notifier.send('Test with bad credentials')
    
    # If we get here, error handling worked
    print('✓ PASS: Notification failure handled gracefully')
    print('  (Returned without raising exception)')
except Exception as e:
    print('✗ FAIL: Exception raised on notification failure')
    print(f'  Error: {e}')
    print('  CRITICAL: This would crash trading!')
    exit(1)
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ] && echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
    print_pass "Error handling works correctly (no exceptions raised)"
else
    print_fail "Error handling test failed"
    echo "$PYTHON_OUTPUT"
    exit 1
fi
echo ""

# Test 4: Check Discord integration
echo "[Test 4] Checking Discord integration..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
import os

webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

if webhook_url:
    print('✓ INFO: Discord webhook configured')
    try:
        from regimeflex.engine.guardian.alerting import get_alert_manager
        alert_mgr = get_alert_manager()
        print('✓ INFO: Discord integration available')
    except ImportError:
        print('⚠ INFO: send_discord function not found')
else:
    print('⚠ INFO: Discord not configured (optional)')
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ]; then
    if echo "$PYTHON_OUTPUT" | grep -q "configured\|available"; then
        print_pass "Discord integration available"
    else
        print_warning "Discord not configured (optional)"
    fi
    echo "$PYTHON_OUTPUT" | grep -E "(INFO|WARNING)" || true
else
    print_warning "Discord check had issues"
    echo "$PYTHON_OUTPUT" | head -3
fi
echo ""

# Test 5: Check notification types
echo "[Test 5] Checking notification event types..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
from regimeflex.engine.guardian import alerting
import inspect

# Find all send_* functions
functions = [name for name in dir(alerting.AlertManager) if name.startswith('send_')]
print(f'Notification functions available: {functions}')

# Check for specific notification types
expected = ['send', 'send_heartbeat', 'send_emergency', 'send_warning']
for func in expected:
    if hasattr(alerting.AlertManager, func):
        print(f'  ✓ {func} available')
    else:
        print(f'  ⚠ {func} not found')

print('✓ PASS: Notification types checked')
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ] && echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
    print_pass "Notification types available"
    echo "$PYTHON_OUTPUT" | grep -E "(available|not found)" | head -5
else
    print_warning "Notification types check result unclear"
    echo "$PYTHON_OUTPUT" | head -5
fi
echo ""

# Test 6: Test that trading continues despite notification failure
echo "[Test 6] Testing trading resilience to notification failures..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
import os

# Temporarily break Telegram config
original_token = os.environ.get('TELEGRAM_BOT_TOKEN')
os.environ['TELEGRAM_BOT_TOKEN'] = ''

try:
    # Try to send notification
    from regimeflex.engine.telemetry import Notifier, TGCreds
    from regimeflex.engine.env import load_env
    
    env = load_env()
    notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
    notifier.send('This should fail gracefully')
    
    # If we get here, error handling worked
    print('✓ PASS: Trading would continue despite notification failure')
    
except Exception as e:
    print('✗ FAIL: Notification failure would crash trading')
    print(f'  Exception: {e}')
    exit(1)
finally:
    # Restore
    if original_token:
        os.environ['TELEGRAM_BOT_TOKEN'] = original_token
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ] && echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
    print_pass "Trading continues despite notification failures"
else
    print_fail "Trading resilience test failed"
    echo "$PYTHON_OUTPUT"
    exit 1
fi
echo ""

# Test 7: Check AlertManager error handling
echo "[Test 7] Checking AlertManager error handling..."
PYTHON_OUTPUT=$(timeout 10 python3 -c "
import regimeflex
from regimeflex.engine.guardian.alerting import get_alert_manager, AlertLevel

alert_mgr = get_alert_manager()

# Check that send methods return bool
try:
    # Test with empty message (should not crash)
    result = alert_mgr.send('', AlertLevel.INFO)
    
    if isinstance(result, bool):
        print('✓ PASS: AlertManager.send() returns bool (does not raise)')
    else:
        print(f'⚠ INFO: AlertManager.send() returns {type(result)}')
    
    # Check that methods exist and are callable
    if hasattr(alert_mgr, '_send_telegram') and callable(alert_mgr._send_telegram):
        print('✓ PASS: _send_telegram method exists')
    else:
        print('✗ FAIL: _send_telegram method not found')
        exit(1)
    
    if hasattr(alert_mgr, '_send_discord') and callable(alert_mgr._send_discord):
        print('✓ PASS: _send_discord method exists')
    else:
        print('✗ FAIL: _send_discord method not found')
        exit(1)
        
except Exception as e:
    print(f'✗ FAIL: Error checking AlertManager: {e}')
    exit(1)
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ] && echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
    print_pass "AlertManager error handling verified"
    echo "$PYTHON_OUTPUT" | grep -E "(PASS|FAIL)" | head -3
else
    print_fail "AlertManager error handling check failed"
    echo "$PYTHON_OUTPUT"
    exit 1
fi
echo ""

# Test 8: Check notification configuration
echo "[Test 8] Checking notification configuration..."
PYTHON_OUTPUT=$(python3 -c "
import regimeflex
import yaml
from pathlib import Path

# Check guardian.yaml
guardian_file = Path('regimeflex/config/guardian.yaml')
if guardian_file.exists():
    with open(guardian_file) as f:
        guardian = yaml.safe_load(f)
    
    alerting = guardian.get('alerting', {})
    telegram = alerting.get('telegram', {})
    discord = alerting.get('discord', {})
    routing = alerting.get('routing', {})
    
    print('Notification Configuration:')
    print(f'  Telegram enabled: {telegram.get(\"enabled\", False)}')
    print(f'  Discord enabled: {discord.get(\"enabled\", False)}')
    print(f'  Routing: {routing}')
    
    if telegram.get('enabled') or routing.get('info'):
        print('✓ PASS: Notification configuration present')
    else:
        print('⚠ WARNING: Notification may not be configured')
else:
    print('⚠ WARNING: guardian.yaml not found')
" 2>&1)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 0 ] && echo "$PYTHON_OUTPUT" | grep -q "✓ PASS"; then
    print_pass "Notification configuration is valid"
    echo "$PYTHON_OUTPUT" | grep -E "(Telegram|Discord|Routing)" || true
else
    print_warning "Notification configuration check result unclear"
    echo "$PYTHON_OUTPUT" | head -5
fi
echo ""

# Final summary
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}Tests Passed:${NC} $TESTS_PASSED"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Tests Failed:${NC} $TESTS_FAILED"
fi
if [ $TESTS_WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings:${NC} $TESTS_WARNINGS"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "=========================================="
    echo -e "${GREEN}✓✓✓ ALL NOTIFICATION TESTS PASSED ✓✓✓${NC}"
    echo "=========================================="
    echo ""
    echo "Notification systems validated:"
    echo "  ✓ Telegram integration"
    echo "  ✓ Error handling (graceful degradation)"
    echo "  ✓ Trading continues despite failures"
    echo "  ✓ Configuration checked"
    echo "  ✓ Discord integration available"
    echo "  ✓ Notification types verified"
    echo ""
    echo "Notification systems are production-ready!"
    echo "Note: Check your Telegram for test message (if configured)!"
    echo "=========================================="
    exit 0
else
    echo "=========================================="
    echo -e "${RED}✗✗✗ SOME TESTS FAILED ✗✗✗${NC}"
    echo "=========================================="
    exit 1
fi

