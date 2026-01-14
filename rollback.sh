#!/bin/bash
set -e

# RegimeFlex Rollback Script
# Usage: ./rollback.sh [backup-timestamp]

BACKUP_TIMESTAMP="${1:-}"
BACKUP_DIR="/opt/regimeflex_backups"
PROJECT_DIR="/opt/regimeflex"

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

# List available backups
if [ -z "$BACKUP_TIMESTAMP" ]; then
    info "Available backups:"
    ls -1t "$BACKUP_DIR"/regimeflex_*.tar.gz 2>/dev/null | head -5 | while read backup; do
        echo "  $(basename $backup)"
    done
    error "Usage: ./rollback.sh <backup-timestamp>"
fi

BACKUP_FILE="$BACKUP_DIR/regimeflex_${BACKUP_TIMESTAMP}.tar.gz"

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

info "Rolling back to: $BACKUP_TIMESTAMP"

# Stop services
info "Stopping services..."
cd "$PROJECT_DIR"
docker-compose down || true
sudo systemctl stop regimeflex.service 2>/dev/null || true

# Backup current state
CURRENT_BACKUP="/opt/regimeflex_backups/pre_rollback_$(date +%Y%m%d_%H%M%S).tar.gz"
info "Creating pre-rollback backup..."
tar -czf "$CURRENT_BACKUP" -C "$(dirname $PROJECT_DIR)" "$(basename $PROJECT_DIR)" \
    --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' 2>/dev/null || true

# Restore backup
info "Restoring backup..."
cd /opt
rm -rf "$PROJECT_DIR"
tar -xzf "$BACKUP_FILE"
cd "$PROJECT_DIR"

# Restart services
info "Starting services..."
docker-compose up -d
sudo systemctl start regimeflex.service 2>/dev/null || true

info "Rollback complete!"
info "Check status: docker-compose ps"
info "View logs: docker-compose logs -f"

