#!/bin/bash
set -e  # Exit on any error

# ==========================================
# PM2 Deployment Validation Script
# ==========================================
# 
# This script validates that RegimeFlex is ready for PM2 deployment
# by testing all aspects of the PM2 configuration and process management.
#
# Usage:
#   chmod +x scripts/test_pm2_deployment.sh
#   ./scripts/test_pm2_deployment.sh
#
# Requirements:
#   - PM2 installed (npm install -g pm2)
#   - Python virtual environment (optional but recommended)
#   - .env file configured
# ==========================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0

# Function to print test header
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo "Date: $(date)"
    echo "Working directory: $(pwd)"
    echo ""
}

# Function to print test result
print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
    ((TESTS_WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ INFO:${NC} $1"
}

# Function to cleanup PM2 processes
cleanup() {
    echo ""
    print_info "Cleaning up PM2 processes..."
    pm2 delete regimeflex-trading 2>/dev/null || true
    pm2 delete regimeflex-watchdog 2>/dev/null || true
    pm2 delete regimeflex-http 2>/dev/null || true
    pm2 kill 2>/dev/null || true
    print_pass "Cleanup complete"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# ==========================================
# Start Validation
# ==========================================
print_header "PM2 Deployment Validation"

# Test 1: PM2 installed?
echo "[Test 1] Checking PM2 installation..."
if ! command -v pm2 &> /dev/null; then
    print_fail "PM2 not installed"
    echo "  Install with: npm install -g pm2"
    exit 1
fi
PM2_VERSION=$(pm2 --version 2>&1 | tail -1)
print_pass "PM2 installed (version $PM2_VERSION)"
echo ""

# Test 2: ecosystem.config.js exists
echo "[Test 2] Checking ecosystem.config.js exists..."
if [ ! -f "ecosystem.config.js" ]; then
    print_fail "ecosystem.config.js not found in current directory"
    exit 1
fi
print_pass "ecosystem.config.js found"
echo ""

# Test 3: ecosystem.config.js syntax
echo "[Test 3] Validating ecosystem.config.js syntax..."
if command -v node &> /dev/null; then
    if node -c ecosystem.config.js 2>/dev/null; then
        print_pass "ecosystem.config.js syntax valid (Node.js check)"
    else
        print_fail "ecosystem.config.js syntax error"
        node -c ecosystem.config.js
        exit 1
    fi
else
    print_warning "Node.js not found, skipping syntax check"
    print_info "Install Node.js for syntax validation: https://nodejs.org/"
fi
echo ""

# Test 4: Python environment
echo "[Test 4] Checking Python environment..."
if [ -d ".venv" ]; then
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        PYTHON_VERSION=$(python --version 2>&1)
        PYTHON_PATH=$(which python)
        print_pass "Virtual environment activated"
        echo "  Python: $PYTHON_VERSION"
        echo "  Path: $PYTHON_PATH"
    else
        print_warning ".venv directory exists but activate script not found"
    fi
else
    print_warning "No .venv directory found"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        print_info "Using system Python: $PYTHON_VERSION"
    else
        print_fail "Python not found"
        exit 1
    fi
fi
echo ""

# Test 5: .env file exists
echo "[Test 5] Checking .env file..."
if [ -f ".env" ]; then
    print_pass ".env file found"
    # Check for required keys (basic check)
    if grep -q "ALPACA_KEY\|APCA_API_KEY_ID" .env 2>/dev/null; then
        print_pass ".env contains Alpaca API key"
    else
        print_warning ".env may be missing Alpaca API key"
    fi
    if grep -q "POLYGON_KEY\|POLYGON_API_KEY" .env 2>/dev/null; then
        print_pass ".env contains Polygon API key"
    else
        print_warning ".env may be missing Polygon API key"
    fi
else
    print_warning ".env file not found"
    print_info "Create .env file from env.example"
fi
echo ""

# Test 6: Project structure
echo "[Test 6] Checking project structure..."
REQUIRED_DIRS=("regimeflex" "regimeflex/config" "regimeflex/engine")
MISSING_DIRS=0
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        print_fail "Required directory missing: $dir"
        ((MISSING_DIRS++))
    fi
done
if [ $MISSING_DIRS -eq 0 ]; then
    print_pass "Project structure valid"
fi
echo ""

# Test 7: RegimeFlex module can be imported
echo "[Test 7] Testing RegimeFlex module import..."
if python3 -c "import regimeflex; print('OK')" 2>/dev/null; then
    print_pass "RegimeFlex module imports successfully"
else
    print_fail "RegimeFlex module import failed"
    python3 -c "import regimeflex" 2>&1 | head -10
    exit 1
fi
echo ""

# Test 8: Start RegimeFlex process with PM2
echo "[Test 8] Starting RegimeFlex process with PM2..."
print_info "Starting process (this may take a few seconds)..."

# Clean up any existing processes first
pm2 delete regimeflex-trading 2>/dev/null || true

# Start the process
if pm2 start ecosystem.config.js --only regimeflex-trading --no-daemon 2>&1 | tee /tmp/pm2_start.log; then
    sleep 5  # Give it time to start
    
    # Check if process is running
    if pm2 list | grep -q "regimeflex-trading.*online\|regimeflex-trading.*errored"; then
        STATUS=$(pm2 jlist | python3 -c "import sys, json; data=json.load(sys.stdin); app=[a for a in data if a['name']=='regimeflex-trading']; print(app[0]['pm2_env']['status'] if app else 'not found')" 2>/dev/null || echo "unknown")
        
        if [ "$STATUS" = "online" ]; then
            print_pass "Process started successfully (status: online)"
        elif [ "$STATUS" = "errored" ]; then
            print_fail "Process started but errored"
            echo ""
            print_info "Last 20 lines of error log:"
            pm2 logs regimeflex-trading --nostream --lines 20 --err
            exit 1
        else
            print_warning "Process status: $STATUS"
        fi
    else
        print_fail "Process failed to start or not found in PM2 list"
        echo ""
        print_info "PM2 process list:"
        pm2 list
        echo ""
        print_info "Startup log:"
        cat /tmp/pm2_start.log
        exit 1
    fi
else
    print_fail "PM2 start command failed"
    cat /tmp/pm2_start.log
    exit 1
fi
echo ""

# Test 9: Environment variables accessible
echo "[Test 9] Checking environment variables in PM2 process..."
sleep 2

# Check PM2 process info
if pm2 show regimeflex-trading | grep -q "PYTHONPATH\|ENV"; then
    print_pass "Environment variables visible in PM2 process info"
    print_info "Environment variables:"
    pm2 show regimeflex-trading | grep -A 10 "env:" | head -5
else
    print_warning "Could not verify environment variables in PM2 info"
fi

# Check logs for environment loading
if pm2 logs regimeflex-trading --nostream --lines 50 2>/dev/null | grep -qi "loaded.*env\|environment.*loaded"; then
    print_pass "Environment loading confirmed in logs"
else
    print_warning "Could not confirm .env loaded from logs (may be normal)"
fi
echo ""

# Test 10: Log files created
echo "[Test 10] Checking log files..."
LOG_DIR="logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    print_info "Created logs directory"
fi

# Check PM2 log files (relative to cwd)
if [ -f "$LOG_DIR/pm2-out.log" ] || [ -f "$LOG_DIR/pm2-error.log" ]; then
    if [ -f "$LOG_DIR/pm2-out.log" ]; then
        OUT_LINES=$(wc -l < "$LOG_DIR/pm2-out.log" 2>/dev/null || echo "0")
        print_pass "PM2 output log created: $LOG_DIR/pm2-out.log ($OUT_LINES lines)"
    fi
    if [ -f "$LOG_DIR/pm2-error.log" ]; then
        ERR_LINES=$(wc -l < "$LOG_DIR/pm2-error.log" 2>/dev/null || echo "0")
        print_pass "PM2 error log created: $LOG_DIR/pm2-error.log ($ERR_LINES lines)"
    fi
else
    # Check PM2's default log location
    PM2_LOG_DIR="$HOME/.pm2/logs"
    if [ -f "$PM2_LOG_DIR/regimeflex-trading-out.log" ] || [ -f "$PM2_LOG_DIR/regimeflex-trading-error.log" ]; then
        print_pass "PM2 log files found in default location: $PM2_LOG_DIR"
    else
        print_warning "PM2 log files not found in expected locations"
        print_info "PM2 may be using different log location"
    fi
fi
echo ""

# Test 11: Heartbeat file updated
echo "[Test 11] Checking Guardian heartbeat..."
sleep 3  # Give runner time to update heartbeat

HEARTBEAT_FILE=".guardian_heartbeat"
if [ -f "$HEARTBEAT_FILE" ]; then
    # Get file modification time (works on both Linux and macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        MOD_TIME=$(stat -f %m "$HEARTBEAT_FILE" 2>/dev/null || echo "0")
    else
        # Linux
        MOD_TIME=$(stat -c %Y "$HEARTBEAT_FILE" 2>/dev/null || echo "0")
    fi
    
    if [ "$MOD_TIME" != "0" ]; then
        CURRENT_TIME=$(date +%s)
        AGE=$((CURRENT_TIME - MOD_TIME))
        
        if [ $AGE -lt 600 ]; then
            print_pass "Heartbeat file updated recently ($AGE seconds ago)"
        else
            print_warning "Heartbeat file is stale ($AGE seconds old)"
        fi
    else
        print_warning "Could not determine heartbeat file age"
    fi
else
    print_warning "Heartbeat file not created yet"
    print_info "This may be normal if runner hasn't completed first cycle"
fi
echo ""

# Test 12: Check for errors in logs
echo "[Test 12] Checking for errors in logs..."
ERROR_COUNT=0

# Check PM2 error log
if [ -f "$LOG_DIR/pm2-error.log" ]; then
    ERROR_COUNT=$(grep -i "error\|exception\|traceback\|fatal" "$LOG_DIR/pm2-error.log" 2>/dev/null | wc -l || echo "0")
fi

# Also check PM2 logs directly
PM2_ERRORS=$(pm2 logs regimeflex-trading --nostream --err --lines 100 2>/dev/null | grep -i "error\|exception\|traceback\|fatal" | wc -l || echo "0")

TOTAL_ERRORS=$((ERROR_COUNT + PM2_ERRORS))

if [ "$TOTAL_ERRORS" -eq 0 ]; then
    print_pass "No errors found in logs"
else
    print_warning "Found $TOTAL_ERRORS error lines in logs"
    print_info "Review logs manually: pm2 logs regimeflex-trading --err"
fi
echo ""

# Test 13: Process status details
echo "[Test 13] Process status details..."
print_info "PM2 process information:"
pm2 show regimeflex-trading | head -25
echo ""

# Test 14: Graceful shutdown
echo "[Test 14] Testing graceful shutdown..."
print_info "Stopping process gracefully..."
pm2 stop regimeflex-trading
sleep 2

STATUS=$(pm2 jlist | python3 -c "import sys, json; data=json.load(sys.stdin); app=[a for a in data if a['name']=='regimeflex-trading']; print(app[0]['pm2_env']['status'] if app else 'not found')" 2>/dev/null || echo "unknown")

if [ "$STATUS" = "stopped" ]; then
    print_pass "Graceful shutdown successful"
else
    print_warning "Process status after stop: $STATUS"
fi
echo ""

# Test 15: Process restart
echo "[Test 15] Testing process restart..."
print_info "Restarting process..."
pm2 restart regimeflex-trading
sleep 3

STATUS=$(pm2 jlist | python3 -c "import sys, json; data=json.load(sys.stdin); app=[a for a in data if a['name']=='regimeflex-trading']; print(app[0]['pm2_env']['status'] if app else 'not found')" 2>/dev/null || echo "unknown")

if [ "$STATUS" = "online" ]; then
    print_pass "Process restarted successfully"
else
    print_fail "Process failed to restart (status: $STATUS)"
    pm2 logs regimeflex-trading --lines 20
    exit 1
fi
echo ""

# Test 16: Memory usage
echo "[Test 16] Checking memory usage..."
MEMORY=$(pm2 jlist | python3 -c "import sys, json; data=json.load(sys.stdin); app=[a for a in data if a['name']=='regimeflex-trading']; print(app[0]['monit']['memory'] if app else '0')" 2>/dev/null || echo "0")

if [ "$MEMORY" != "0" ]; then
    MEMORY_MB=$((MEMORY / 1024 / 1024))
    print_pass "Memory usage: ${MEMORY_MB}MB"
    if [ $MEMORY_MB -gt 1024 ]; then
        print_warning "Memory usage exceeds 1GB (${MEMORY_MB}MB)"
    fi
else
    print_warning "Could not determine memory usage"
fi
echo ""

# ==========================================
# Final Summary
# ==========================================
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
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
    echo -e "${GREEN}✓✓✓ ALL CRITICAL TESTS PASSED ✓✓✓${NC}"
    echo "=========================================="
    echo ""
    echo "PM2 deployment is ready for production!"
    echo ""
    echo "Next steps:"
    echo "  1. Review logs: pm2 logs regimeflex-trading"
    echo "  2. Monitor: pm2 monit"
    echo "  3. Save config: pm2 save"
    echo "  4. Auto-start on boot: pm2 startup"
    echo ""
    echo "To deploy to production:"
    echo "  pm2 start ecosystem.config.js"
    echo "  pm2 save"
    echo "  pm2 startup  # (run as root/sudo)"
    echo ""
    echo "Useful commands:"
    echo "  pm2 status                    # Check process status"
    echo "  pm2 logs regimeflex-trading    # View logs"
    echo "  pm2 restart regimeflex-trading # Restart process"
    echo "  pm2 stop regimeflex-trading    # Stop process"
    echo "  pm2 delete regimeflex-trading  # Remove process"
    echo "=========================================="
    exit 0
else
    echo "=========================================="
    echo -e "${RED}✗✗✗ SOME TESTS FAILED ✗✗✗${NC}"
    echo "=========================================="
    echo ""
    echo "Please review the errors above and fix them before deploying."
    echo ""
    echo "Common issues:"
    echo "  - Missing .env file or API keys"
    echo "  - Python virtual environment not set up"
    echo "  - PM2 not installed"
    echo "  - ecosystem.config.js syntax errors"
    echo "=========================================="
    exit 1
fi

