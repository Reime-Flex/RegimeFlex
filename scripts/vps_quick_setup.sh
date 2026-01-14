#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo "=========================================="
echo "RegimeFlex VPS Quick Setup"
echo "=========================================="
echo "User: $(whoami)"
echo "Host: $(hostname)"
echo ""

echo -e "${BLUE}${BOLD}[Step 1/6] Installing Python 3.12...${NC}"
echo ""
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
python3.12 --version
echo -e "${GREEN}✓ Python 3.12 installed${NC}"
echo ""

echo -e "${BLUE}${BOLD}[Step 2/6] Cloning RegimeFlex...${NC}"
echo ""
cd ~
git clone https://github.com/Reime-Flex/RegimeFlex.git
cd RegimeFlex
echo -e "${GREEN}✓ RegimeFlex cloned${NC}"
echo ""

echo -e "${BLUE}${BOLD}[Step 3/6] Setting Up Python Environment...${NC}"
echo ""
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

echo -e "${BLUE}${BOLD}[Step 4/6] Creating Directory Structure...${NC}"
echo ""
mkdir -p data/state logs/trading logs/audit reports
chmod 755 data
chmod 700 data/state
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

echo -e "${BLUE}${BOLD}[Step 5/6] Creating .env Template...${NC}"
echo ""
cat > .env << 'EOF'
ALPACA_KEY=YOUR_PAPER_KEY_HERE
ALPACA_SECRET=YOUR_PAPER_SECRET_HERE
ALPACA_BASE_URL=https://paper-api.alpaca.markets
POLYGON_KEY=YOUR_POLYGON_KEY_HERE
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE
ENV=prod
EOF
chmod 600 .env
echo -e "${GREEN}✓ .env created${NC}"
echo -e "${YELLOW}⚠️  Edit .env with your API keys!${NC}"
echo ""

echo -e "${BLUE}${BOLD}[Step 6/6] Configuring PM2...${NC}"
echo ""
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'regimeflex-trading',
    script: 'python',
    args: ['-m', 'regimeflex', 'run'],
    cwd: '$HOME/RegimeFlex',
    interpreter: 'none',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    max_restarts: 10,
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    env: {
      PYTHONPATH: '$HOME/RegimeFlex',
      PATH: '$HOME/RegimeFlex/.venv/bin:\$PATH',
      ENV: 'prod'
    }
  }]
}
EOF
pm2 ecosystem ecosystem.config.js
echo -e "${GREEN}✓ PM2 configured${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}${BOLD}✓✓✓ SETUP COMPLETE ✓✓✓${NC}"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Edit .env: nano ~/RegimeFlex/.env"
echo "2. Test: cd ~/RegimeFlex && source .venv/bin/activate && python -c 'import regimeflex'"
echo "3. Start: pm2 start ecosystem.config.js"
echo "=========================================="

