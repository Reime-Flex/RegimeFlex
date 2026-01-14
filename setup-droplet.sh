#!/bin/bash
set -e

# RegimeFlex Droplet Initial Setup Script
# Run this ONCE on a fresh DigitalOcean droplet
# Usage: sudo bash setup-droplet.sh

if [ "$EUID" -ne 0 ]; then 
    echo "Error: Please run as root or with sudo"
    exit 1
fi

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${GREEN}$1${NC}"
}

section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

section "Updating System"
apt-get update
apt-get upgrade -y

section "Installing Docker"
if ! command -v docker &> /dev/null; then
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    info "Docker installed"
else
    info "Docker already installed"
fi

section "Installing Docker Compose (standalone)"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    info "Docker Compose installed"
else
    info "Docker Compose already installed"
fi

section "Installing Nginx"
apt-get install -y nginx

section "Installing Certbot"
apt-get install -y certbot python3-certbot-nginx

section "Creating RegimeFlex User"
if ! id "regimeflex" &>/dev/null; then
    useradd -m -s /bin/bash regimeflex
    usermod -aG docker regimeflex
    info "User 'regimeflex' created"
else
    info "User 'regimeflex' already exists"
fi

section "Setting Up Firewall (UFW)"
ufw --force enable
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw status

section "Creating Directories"
mkdir -p /opt/regimeflex
mkdir -p /opt/regimeflex_backups
mkdir -p /var/www/certbot
chown -R regimeflex:regimeflex /opt/regimeflex
chown -R regimeflex:regimeflex /opt/regimeflex_backups

section "Setting Up Systemd Service"
cp /opt/regimeflex/systemd/regimeflex.service /etc/systemd/system/ 2>/dev/null || echo "Service file will be copied during deployment"
systemctl daemon-reload

info "\n=== Setup Complete ==="
info "Next steps:"
info "1. Deploy the application: ./deploy.sh <droplet-ip>"
info "2. Configure Nginx and SSL (see DEPLOYMENT.md)"
info "3. Enable systemd service: systemctl enable regimeflex.service"

