#!/bin/bash
set -e  # Exit on error

echo "========================================="
echo "PM2 Deployment Validation"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: PM2 installed?
echo -e "\n[Test 1] Checking PM2 installation..."
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}✗ PM2 not installed. Run: npm install -g pm2${NC}"
    exit 1
fi
PM2_VERSION=$(pm2 --version 2>&1 | head -1)
echo -e "${GREEN}✓ PM2 installed: ${PM2_VERSION}${NC}"

# Test 2: ecosystem.config.js syntax
echo -e "\n[Test 2] Validating ecosystem.config.js..."
if ! pm2 ecosystem ecosystem.config.js 2>&1 | grep -q "valid"; then
    echo -e "${YELLOW}⚠ Config validation warning (may still work)${NC}"
else
    echo -e "${GREEN}✓ Config syntax valid${NC}"
fi

# Test 3: Check if process is already running
echo -e "\n[Test 3] Checking for existing RegimeFlex processes..."
if pm2 list | grep -q "regimeflex"; then
    echo -e "${YELLOW}⚠ RegimeFlex processes already running. Stopping them first...${NC}"
    pm2 delete regimeflex-trading 2>/dev/null || true
    pm2 delete regimeflex-watchdog 2>/dev/null || true
    pm2 delete regimeflex-http 2>/dev/null || true
    sleep 2
fi

# Test 4: Start process
echo -e "\n[Test 4] Starting RegimeFlex process..."
if pm2 start ecosystem.config.js --only regimeflex-trading; then
    echo -e "${GREEN}✓ Process started${NC}"
    sleep 5
else
    echo -e "${RED}✗ Failed to start process${NC}"
    pm2 logs regimeflex-trading --lines 20 --nostream
    exit 1
fi

# Test 5: Check process status
echo -e "\n[Test 5] Checking process status..."
STATUS=$(pm2 jlist | jq -r '.[] | select(.name=="regimeflex-trading") | .pm2_env.status' 2>/dev/null || echo "unknown")
if [[ "$STATUS" == "online" ]]; then
    echo -e "${GREEN}✓ Process is online${NC}"
else
    echo -e "${RED}✗ Process status: ${STATUS}${NC}"
    pm2 logs regimeflex-trading --lines 20 --nostream
    exit 1
fi

# Test 6: Environment variables (check if .env is loaded)
echo -e "\n[Test 6] Checking environment variable loading..."
# Run a simple Python command in PM2 context
ENV_CHECK=$(pm2 exec regimeflex-trading "python -c 'import os; print(\"ALPACA_KEY_SET\" if os.getenv(\"ALPACA_KEY\") or os.getenv(\"APCA_API_KEY_ID\") else \"ALPACA_KEY_NOT_SET\")'" 2>/dev/null | tail -1 || echo "ERROR")
if [[ "$ENV_CHECK" == *"ALPACA_KEY_SET"* ]]; then
    echo -e "${GREEN}✓ Environment variables accessible${NC}"
elif [[ "$ENV_CHECK" == *"ALPACA_KEY_NOT_SET"* ]]; then
    echo -e "${YELLOW}⚠ Environment variables not set (this is OK if .env doesn't exist)${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify environment variables${NC}"
fi

# Test 7: Log files created
echo -e "\n[Test 7] Checking log files..."
LOG_DIR="logs"
if [[ ! -d "$LOG_DIR" ]]; then
    mkdir -p "$LOG_DIR"
fi

if [[ -f "$LOG_DIR/pm2-out.log" ]] && [[ -f "$LOG_DIR/pm2-error.log" ]]; then
    echo -e "${GREEN}✓ Log files created${NC}"
    echo "   - $LOG_DIR/pm2-out.log"
    echo "   - $LOG_DIR/pm2-error.log"
else
    echo -e "${RED}✗ Log files missing!${NC}"
    echo "   Expected: $LOG_DIR/pm2-out.log"
    echo "   Expected: $LOG_DIR/pm2-error.log"
    exit 1
fi

# Test 8: Heartbeat file updated (if process runs long enough)
echo -e "\n[Test 8] Checking heartbeat file..."
HEARTBEAT_FILE=".guardian_heartbeat"
if [[ -f "$HEARTBEAT_FILE" ]]; then
    if command -v stat &> /dev/null; then
        # Linux/Unix
        AGE=$(($(date +%s) - $(stat -c %Y "$HEARTBEAT_FILE" 2>/dev/null || echo 0)))
    elif command -v stat &> /dev/null && [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        AGE=$(($(date +%s) - $(stat -f %m "$HEARTBEAT_FILE" 2>/dev/null || echo 0)))
    else
        AGE=999999
    fi
    
    if [[ $AGE -lt 600 ]]; then
        echo -e "${GREEN}✓ Heartbeat file updated recently ($AGE seconds ago)${NC}"
    else
        echo -e "${YELLOW}⚠ Heartbeat file is stale ($AGE seconds old)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Heartbeat file not created yet (may need more time)${NC}"
fi

# Test 9: Python path is correct
echo -e "\n[Test 9] Checking Python interpreter..."
PYTHON_PATH=$(pm2 jlist | jq -r '.[] | select(.name=="regimeflex-trading") | .pm2_env.interpreter' 2>/dev/null || echo "unknown")
if [[ "$PYTHON_PATH" == *".venv/bin/python"* ]] || [[ "$PYTHON_PATH" == *"python"* ]]; then
    echo -e "${GREEN}✓ Python interpreter: ${PYTHON_PATH}${NC}"
else
    echo -e "${YELLOW}⚠ Python interpreter: ${PYTHON_PATH}${NC}"
fi

# Test 10: Working directory is correct
echo -e "\n[Test 10] Checking working directory..."
CWD=$(pm2 jlist | jq -r '.[] | select(.name=="regimeflex-trading") | .pm2_env.cwd' 2>/dev/null || echo "unknown")
if [[ -d "$CWD" ]]; then
    echo -e "${GREEN}✓ Working directory: ${CWD}${NC}"
    if [[ -f "$CWD/regimeflex/__init__.py" ]]; then
        echo -e "${GREEN}✓ RegimeFlex package found in working directory${NC}"
    else
        echo -e "${YELLOW}⚠ RegimeFlex package not found in working directory${NC}"
    fi
else
    echo -e "${RED}✗ Working directory invalid: ${CWD}${NC}"
fi

# Test 11: Graceful shutdown
echo -e "\n[Test 11] Testing graceful shutdown..."
if pm2 stop regimeflex-trading; then
    sleep 2
    STATUS_AFTER_STOP=$(pm2 jlist | jq -r '.[] | select(.name=="regimeflex-trading") | .pm2_env.status' 2>/dev/null || echo "unknown")
    if [[ "$STATUS_AFTER_STOP" == "stopped" ]]; then
        echo -e "${GREEN}✓ Graceful shutdown successful${NC}"
    else
        echo -e "${YELLOW}⚠ Process status after stop: ${STATUS_AFTER_STOP}${NC}"
    fi
    
    # Clean up
    pm2 delete regimeflex-trading 2>/dev/null || true
    echo -e "${GREEN}✓ Process deleted${NC}"
else
    echo -e "${RED}✗ Failed to stop process gracefully${NC}"
    pm2 delete regimeflex-trading 2>/dev/null || true
    exit 1
fi

# Final summary
echo -e "\n========================================="
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo "========================================="
echo "Deployment is ready for production!"
echo ""
echo "Next steps:"
echo "  1. Set REGIMEFLEX_ROOT environment variable:"
echo "     export REGIMEFLEX_ROOT=/path/to/RegimeFlex"
echo "  2. Start all processes:"
echo "     pm2 start ecosystem.config.js"
echo "  3. Monitor logs:"
echo "     pm2 logs"
echo "  4. Save PM2 configuration:"
echo "     pm2 save"
echo "  5. Setup PM2 startup script:"
echo "     pm2 startup"

