#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# Script info
SCRIPT_NAME="RegimeFlex VPS Setup - Step 1: Initial Setup"
SCRIPT_VERSION="1.0.0"

echo "=========================================="
echo -e "${BOLD}${SCRIPT_NAME}${NC}"
echo "=========================================="
echo ""
echo "Target: DigitalOcean Droplet (Ubuntu 22.04)"
echo "Purpose: Production RegimeFlex deployment"
echo "Date: $(date)"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Error: Please run as root or with sudo${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Check Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        echo -e "${YELLOW}⚠ Warning: This script is designed for Ubuntu${NC}"
        echo "Detected OS: $ID"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo -e "${GREEN}✓ OS: $PRETTY_NAME${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Could not detect OS version${NC}"
fi
echo ""

# Step 1: System update
echo -e "${BLUE}[Step 1/9] Updating system packages...${NC}"
apt update
apt upgrade -y
apt autoremove -y
apt autoclean
echo -e "${GREEN}✓ System updated and upgraded${NC}"
echo ""

# Step 2: Install essential packages
echo -e "${BLUE}[Step 2/9] Installing essential packages...${NC}"
apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    ufw \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    unzip \
    zip \
    net-tools \
    dnsutils \
    jq
echo -e "${GREEN}✓ Essential packages installed${NC}"
echo ""

# Step 3: Configure timezone
echo -e "${BLUE}[Step 3/9] Setting timezone to America/New_York...${NC}"
timedatectl set-timezone America/New_York
TIMEZONE=$(timedatectl | grep 'Time zone' | awk '{print $3}')
echo -e "${GREEN}✓ Timezone set: $TIMEZONE${NC}"
echo "Current time: $(date)"
echo ""

# Step 4: Configure locale
echo -e "${BLUE}[Step 4/9] Configuring locale...${NC}"
if ! locale -a | grep -q "en_US.utf8"; then
    locale-gen en_US.UTF-8
fi
update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
echo -e "${GREEN}✓ Locale configured: en_US.UTF-8${NC}"
echo ""

# Step 5: Install Python 3.12
echo -e "${BLUE}[Step 5/9] Installing Python 3.12...${NC}"

# Check if Python 3.12 is already installed
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version)
    echo -e "${GREEN}✓ Python 3.12 already installed: $PYTHON_VERSION${NC}"
else
    # Add deadsnakes PPA
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    
    # Install Python 3.12 and dependencies
    apt install -y \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3.12-distutils \
        python3-pip
    
    # Make python3.12 the default python3
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    
    # Verify installation
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python 3.12 installed: $PYTHON_VERSION${NC}"
fi

# Upgrade pip
python3 -m pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip upgraded: $(python3 -m pip --version | cut -d' ' -f2)${NC}"
echo ""

# Step 6: Install Node.js 20.x
echo -e "${BLUE}[Step 6/9] Installing Node.js 20.x...${NC}"

# Check if Node.js is already installed
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js already installed: $NODE_VERSION${NC}"
    
    # Check if it's version 20.x
    if [[ ! "$NODE_VERSION" =~ ^v20\. ]]; then
        echo -e "${YELLOW}⚠ Warning: Node.js version is not 20.x (found: $NODE_VERSION)${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    # Install Node.js 20.x from NodeSource
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
    
    # Verify installation
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓ Node.js installed: $NODE_VERSION${NC}"
    echo -e "${GREEN}✓ npm installed: $NPM_VERSION${NC}"
fi
echo ""

# Step 7: Install PM2
echo -e "${BLUE}[Step 7/9] Installing PM2 globally...${NC}"

# Check if PM2 is already installed
if command -v pm2 &> /dev/null; then
    PM2_VERSION=$(pm2 --version)
    echo -e "${GREEN}✓ PM2 already installed: $PM2_VERSION${NC}"
else
    npm install -g pm2
    
    # Verify installation
    PM2_VERSION=$(pm2 --version)
    echo -e "${GREEN}✓ PM2 installed: $PM2_VERSION${NC}"
    
    # Setup PM2 startup script
    echo -e "${BLUE}Setting up PM2 startup script...${NC}"
    pm2 startup systemd -u $SUDO_USER --hp /home/$SUDO_USER || true
    echo -e "${GREEN}✓ PM2 startup configured${NC}"
fi
echo ""

# Step 8: Configure basic firewall
echo -e "${BLUE}[Step 8/9] Configuring firewall (UFW)...${NC}"

# Check if UFW is active
if ufw status | grep -q "Status: active"; then
    echo -e "${GREEN}✓ Firewall already active${NC}"
else
    # Enable firewall
    ufw --force enable
    
    # Allow SSH (critical - don't lock yourself out!)
    ufw allow 22/tcp comment 'SSH'
    
    # Allow HTTP/HTTPS (optional, for web services)
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # Allow custom ports if needed (e.g., for Flask API)
    # ufw allow 5000/tcp comment 'Flask API'
    
    echo -e "${GREEN}✓ Firewall enabled and configured${NC}"
fi

# Show firewall status
echo ""
echo "Firewall status:"
ufw status numbered
echo ""

# Step 9: System verification
echo -e "${BLUE}[Step 9/9] Verifying installations...${NC}"

VERIFICATION_PASSED=true

# Verify Python
if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version)
    echo -e "${GREEN}✓ Python: $PYTHON_VER${NC}"
else
    echo -e "${RED}✗ Python not found${NC}"
    VERIFICATION_PASSED=false
fi

# Verify pip
if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
    PIP_VER=$(python3 -m pip --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ pip: $PIP_VER${NC}"
else
    echo -e "${RED}✗ pip not found${NC}"
    VERIFICATION_PASSED=false
fi

# Verify Node.js
if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    echo -e "${GREEN}✓ Node.js: $NODE_VER${NC}"
else
    echo -e "${RED}✗ Node.js not found${NC}"
    VERIFICATION_PASSED=false
fi

# Verify npm
if command -v npm &> /dev/null; then
    NPM_VER=$(npm --version)
    echo -e "${GREEN}✓ npm: $NPM_VER${NC}"
else
    echo -e "${RED}✗ npm not found${NC}"
    VERIFICATION_PASSED=false
fi

# Verify PM2
if command -v pm2 &> /dev/null; then
    PM2_VER=$(pm2 --version)
    echo -e "${GREEN}✓ PM2: $PM2_VER${NC}"
else
    echo -e "${RED}✗ PM2 not found${NC}"
    VERIFICATION_PASSED=false
fi

# Verify timezone
TIMEZONE_CHECK=$(timedatectl | grep 'Time zone' | awk '{print $3}')
if [ "$TIMEZONE_CHECK" = "America/New_York" ]; then
    echo -e "${GREEN}✓ Timezone: $TIMEZONE_CHECK${NC}"
else
    echo -e "${YELLOW}⚠ Timezone: $TIMEZONE_CHECK (expected: America/New_York)${NC}"
fi

echo ""

# Final Summary
echo "=========================================="
if [ "$VERIFICATION_PASSED" = true ]; then
    echo -e "${GREEN}${BOLD}✓✓✓ STEP 1 COMPLETE ✓✓✓${NC}"
    echo "=========================================="
    echo ""
    echo "Installed Components:"
    echo "  - Python: $(python3 --version)"
    echo "  - pip: $(python3 -m pip --version | cut -d' ' -f2)"
    echo "  - Node.js: $(node --version)"
    echo "  - npm: $(npm --version)"
    echo "  - PM2: $(pm2 --version)"
    echo "  - Timezone: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
    echo "  - Locale: en_US.UTF-8"
    echo ""
    echo "System Information:"
    echo "  - OS: $(lsb_release -d | cut -f2)"
    echo "  - Kernel: $(uname -r)"
    echo "  - Uptime: $(uptime -p)"
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo "  1. Create non-root user (if not exists):"
    echo "     adduser regimeflex"
    echo ""
    echo "  2. Run Step 2: User setup and RegimeFlex installation"
    echo "     sudo -u regimeflex bash scripts/vps_setup_step2_user.sh"
    echo ""
    echo "  3. Or manually:"
    echo "     - Clone RegimeFlex repository"
    echo "     - Set up virtual environment"
    echo "     - Install dependencies"
    echo "     - Configure environment variables"
    echo ""
    echo "=========================================="
    exit 0
else
    echo -e "${RED}${BOLD}✗✗✗ STEP 1 INCOMPLETE ✗✗✗${NC}"
    echo "=========================================="
    echo ""
    echo "Some verifications failed. Please review the output above."
    echo "Fix any issues before proceeding to Step 2."
    echo ""
    exit 1
fi

