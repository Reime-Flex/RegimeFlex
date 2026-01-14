#!/bin/bash
# Script to check if RegimeFlex is deployed on VPS

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "RegimeFlex VPS Deployment Check"
echo "=========================================="
echo ""

# Check if running on VPS (Linux) or locally
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}⚠️  This script is designed to run on your VPS (Linux)${NC}"
    echo "To check remotely, SSH into your VPS first:"
    echo "  ssh user@your-vps-ip"
    echo ""
    echo "Then run this script on the VPS."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Checking RegimeFlex deployment status...${NC}"
echo ""

DEPLOYED=false
ISSUES=0

# Check 1: Is RegimeFlex directory present?
echo -e "${BLUE}[Check 1] Looking for RegimeFlex directory...${NC}"
POSSIBLE_PATHS=(
    "$HOME/RegimeFlex"
    "$HOME/regimeflex"
    "/home/regimeflex/RegimeFlex"
    "/opt/regimeflex"
    "$(pwd)"
)

FOUND_PATH=""
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ] && [ -f "$path/regimeflex/__init__.py" ]; then
        FOUND_PATH="$path"
        echo -e "${GREEN}✓ Found RegimeFlex at: $FOUND_PATH${NC}"
        cd "$FOUND_PATH"
        break
    fi
done

if [ -z "$FOUND_PATH" ]; then
    echo -e "${RED}✗ RegimeFlex directory not found${NC}"
    echo "  Searched in:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        echo "    - $path"
    done
    ISSUES=$((ISSUES + 1))
else
    DEPLOYED=true
fi
echo ""

# Check 2: Is Python virtual environment present?
if [ "$DEPLOYED" = true ]; then
    echo -e "${BLUE}[Check 2] Checking Python virtual environment...${NC}"
    if [ -d ".venv" ] || [ -d ".venv312" ] || [ -d "venv" ]; then
        VENV_PATH=""
        [ -d ".venv" ] && VENV_PATH=".venv"
        [ -d ".venv312" ] && VENV_PATH=".venv312"
        [ -d "venv" ] && VENV_PATH="venv"
        echo -e "${GREEN}✓ Virtual environment found: $VENV_PATH${NC}"
        
        # Check Python version
        if [ -f "$VENV_PATH/bin/python" ]; then
            PYTHON_VERSION=$("$VENV_PATH/bin/python" --version 2>&1)
            echo -e "${GREEN}  Python: $PYTHON_VERSION${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
        ISSUES=$((ISSUES + 1))
    fi
    echo ""
fi

# Check 3: Are dependencies installed?
if [ "$DEPLOYED" = true ]; then
    echo -e "${BLUE}[Check 3] Checking if dependencies are installed...${NC}"
    if [ -f "requirements.txt" ]; then
        if [ -d ".venv" ] || [ -d ".venv312" ] || [ -d "venv" ]; then
            VENV_BIN=""
            [ -d ".venv" ] && VENV_BIN=".venv/bin"
            [ -d ".venv312" ] && VENV_BIN=".venv312/bin"
            [ -d "venv" ] && VENV_BIN="venv/bin"
            
            if [ -f "$VENV_BIN/python" ]; then
                # Try to import regimeflex
                if "$VENV_BIN/python" -c "import regimeflex" 2>/dev/null; then
                    echo -e "${GREEN}✓ RegimeFlex package is importable${NC}"
                else
                    echo -e "${YELLOW}⚠ RegimeFlex package not importable (may need: pip install -e .)${NC}"
                    ISSUES=$((ISSUES + 1))
                fi
            fi
        fi
    else
        echo -e "${YELLOW}⚠ requirements.txt not found${NC}"
    fi
    echo ""
fi

# Check 4: Is PM2 installed and running RegimeFlex?
echo -e "${BLUE}[Check 4] Checking PM2 processes...${NC}"
if command -v pm2 &> /dev/null; then
    PM2_VERSION=$(pm2 --version)
    echo -e "${GREEN}✓ PM2 installed: v$PM2_VERSION${NC}"
    
    # Check for RegimeFlex processes
    PM2_LIST=$(pm2 list 2>/dev/null)
    if echo "$PM2_LIST" | grep -qi "regimeflex"; then
        echo -e "${GREEN}✓ RegimeFlex processes found in PM2:${NC}"
        pm2 list | grep -i regimeflex
        echo ""
        echo "PM2 Status:"
        pm2 status | grep -i regimeflex || echo "  (check 'pm2 list' for details)"
    else
        echo -e "${YELLOW}⚠ No RegimeFlex processes found in PM2${NC}"
        echo "  Run: pm2 start ecosystem.config.js"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${YELLOW}⚠ PM2 not installed${NC}"
    echo "  Install with: npm install -g pm2"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# Check 5: Is ecosystem.config.js present?
if [ "$DEPLOYED" = true ]; then
    echo -e "${BLUE}[Check 5] Checking PM2 configuration...${NC}"
    if [ -f "ecosystem.config.js" ]; then
        echo -e "${GREEN}✓ ecosystem.config.js found${NC}"
    else
        echo -e "${YELLOW}⚠ ecosystem.config.js not found${NC}"
        ISSUES=$((ISSUES + 1))
    fi
    echo ""
fi

# Check 6: Is .env file configured?
if [ "$DEPLOYED" = true ]; then
    echo -e "${BLUE}[Check 6] Checking environment configuration...${NC}"
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓ .env file found${NC}"
        # Check for critical variables (without showing values)
        if grep -q "ALPACA_KEY" .env && grep -q "ALPACA_SECRET" .env; then
            if grep -q "ALPACA_KEY=YOUR_" .env || grep -q "ALPACA_SECRET=YOUR_" .env; then
                echo -e "${YELLOW}⚠ .env file contains placeholder values${NC}"
                ISSUES=$((ISSUES + 1))
            else
                echo -e "${GREEN}✓ .env appears to be configured${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ .env missing ALPACA credentials${NC}"
            ISSUES=$((ISSUES + 1))
        fi
    else
        echo -e "${YELLOW}⚠ .env file not found${NC}"
        echo "  Create from: cp env.example .env"
        ISSUES=$((ISSUES + 1))
    fi
    echo ""
fi

# Check 7: Are required directories present?
if [ "$DEPLOYED" = true ]; then
    echo -e "${BLUE}[Check 7] Checking directory structure...${NC}"
    REQUIRED_DIRS=("data/state" "logs/trading" "logs/audit")
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo -e "${GREEN}✓ $dir exists${NC}"
        else
            echo -e "${YELLOW}⚠ $dir missing${NC}"
            ISSUES=$((ISSUES + 1))
        fi
    done
    echo ""
fi

# Check 8: Is HTTP server responding?
echo -e "${BLUE}[Check 8] Checking if HTTP server is running...${NC}"
if command -v curl &> /dev/null; then
    # Check common ports
    for port in 8080 5000 3000; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ HTTP server responding on port $port${NC}"
            curl -s "http://localhost:$port/health" | head -1
        fi
    done
    
    # If no response, check if process is listening
    if command -v netstat &> /dev/null || command -v ss &> /dev/null; then
        LISTENING=$(netstat -tuln 2>/dev/null | grep -E ":(8080|5000|3000)" || ss -tuln 2>/dev/null | grep -E ":(8080|5000|3000)")
        if [ -n "$LISTENING" ]; then
            echo -e "${YELLOW}⚠ Ports are listening but /health endpoint not responding${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ curl not available (cannot test HTTP endpoints)${NC}"
fi
echo ""

# Summary
echo "=========================================="
if [ "$DEPLOYED" = true ] && [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ REGIMEFLEX IS DEPLOYED AND READY ✓✓✓${NC}"
    echo "=========================================="
    echo ""
    echo "Quick Commands:"
    echo "  View logs:    pm2 logs"
    echo "  Check status: pm2 status"
    echo "  Restart:      pm2 restart ecosystem.config.js"
    echo "  Stop:         pm2 stop ecosystem.config.js"
elif [ "$DEPLOYED" = true ] && [ "$ISSUES" -gt 0 ]; then
    echo -e "${YELLOW}⚠ REGIMEFLEX IS DEPLOYED BUT NEEDS ATTENTION${NC}"
    echo "=========================================="
    echo ""
    echo "Found $ISSUES issue(s) - see details above"
    echo ""
    echo "Common fixes:"
    echo "  1. Install dependencies: pip install -r requirements.txt"
    echo "  2. Install package: pip install -e ."
    echo "  3. Configure .env: cp env.example .env && nano .env"
    echo "  4. Start PM2: pm2 start ecosystem.config.js"
else
    echo -e "${RED}✗ REGIMEFLEX IS NOT DEPLOYED${NC}"
    echo "=========================================="
    echo ""
    echo "To deploy, run:"
    echo "  bash scripts/vps_quick_setup.sh"
    echo ""
    echo "Or follow the manual setup in:"
    echo "  regimeflex/docs/DEPLOYMENT.md"
fi
echo ""

