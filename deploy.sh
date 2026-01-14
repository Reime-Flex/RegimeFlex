#!/bin/bash
set -e

# RegimeFlex One-Command Deploy Script
# Usage: ./deploy.sh [droplet-ip] [deploy-user]

DROPLET_IP="${1:-}"
DEPLOY_USER="${2:-regimeflex}"
PROJECT_DIR="/opt/regimeflex"
REMOTE_SCRIPT="/tmp/regimeflex_deploy_remote.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

# Check if droplet IP is provided
if [ -z "$DROPLET_IP" ]; then
    error "Usage: ./deploy.sh <droplet-ip> [deploy-user]"
fi

# Check if SSH key is available
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${DEPLOY_USER}@${DROPLET_IP}" exit 2>/dev/null; then
    warn "SSH key authentication may not be set up. You may be prompted for a password."
fi

info "Deploying RegimeFlex to ${DEPLOY_USER}@${DROPLET_IP}..."

# Create remote deploy script
cat > "$REMOTE_SCRIPT" << 'REMOTE_SCRIPT_EOF'
#!/bin/bash
set -e

PROJECT_DIR="/opt/regimeflex"
BACKUP_DIR="/opt/regimeflex_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cd "$PROJECT_DIR" || exit 1

# Create backup
info() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1"; }

info "Creating backup..."
mkdir -p "$BACKUP_DIR"
if [ -d "$PROJECT_DIR" ]; then
    tar -czf "$BACKUP_DIR/regimeflex_${TIMESTAMP}.tar.gz" \
        -C "$(dirname $PROJECT_DIR)" \
        "$(basename $PROJECT_DIR)" \
        --exclude='node_modules' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.git' 2>/dev/null || true
    info "Backup created: regimeflex_${TIMESTAMP}.tar.gz"
fi

# Pull latest code (if git repo)
if [ -d "$PROJECT_DIR/.git" ]; then
    info "Pulling latest code..."
    git pull origin main || git pull origin master || warn "Git pull failed, continuing..."
fi

# Stop services
info "Stopping services..."
cd "$PROJECT_DIR"
sudo systemctl stop regimeflex.service 2>/dev/null || docker-compose down 2>/dev/null || true

# Build and start
info "Building and starting services..."
cd "$PROJECT_DIR"
docker-compose build --no-cache
docker-compose up -d

# Wait for health checks
info "Waiting for services to be healthy..."
sleep 10

# Check health
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    info "Backend health check passed"
else
    warn "Backend health check failed - check logs: docker-compose logs backend"
fi

if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    info "Frontend health check passed"
else
    warn "Frontend health check failed - check logs: docker-compose logs frontend"
fi

# Install systemd service if not exists
if [ ! -f /etc/systemd/system/regimeflex.service ] && [ -f "$PROJECT_DIR/systemd/regimeflex.service" ]; then
    info "Installing systemd service..."
    sudo cp "$PROJECT_DIR/systemd/regimeflex.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable regimeflex.service
fi

# Restart systemd service if it exists
if systemctl is-enabled regimeflex.service > /dev/null 2>&1; then
    info "Restarting systemd service..."
    sudo systemctl restart regimeflex.service
fi

info "Deployment complete!"
info "View logs: docker-compose logs -f"
info "Check status: docker-compose ps"
REMOTE_SCRIPT_EOF

# Copy files to droplet
info "Copying files to droplet..."
rsync -avz --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='data/cache' \
    --exclude='logs' \
    ./ "${DEPLOY_USER}@${DROPLET_IP}:${PROJECT_DIR}/"

# Copy and execute remote script
info "Executing deployment on droplet..."
scp "$REMOTE_SCRIPT" "${DEPLOY_USER}@${DROPLET_IP}:${REMOTE_SCRIPT}"
ssh "${DEPLOY_USER}@${DROPLET_IP}" "chmod +x ${REMOTE_SCRIPT} && sudo -E ${REMOTE_SCRIPT}"

# Cleanup
rm -f "$REMOTE_SCRIPT"

info "Deployment complete!"
info "SSH into droplet: ssh ${DEPLOY_USER}@${DROPLET_IP}"
info "View logs: ssh ${DEPLOY_USER}@${DROPLET_IP} 'cd ${PROJECT_DIR} && docker-compose logs -f'"

