#!/bin/bash
# Validation script to test deployment locally before deploying to droplet

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() {
    echo -e "${GREEN}✓ $1${NC}"
    PASS=$((PASS + 1))
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    FAIL=$((FAIL + 1))
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "=========================================="
echo "RegimeFlex Deployment Validation"
echo "=========================================="
echo ""

# Check Docker
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    pass "Docker installed"
    docker --version
else
    fail "Docker not installed"
    exit 1
fi

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    pass "Docker Compose available"
else
    fail "Docker Compose not available"
    exit 1
fi

echo ""

# Check files
echo "Checking deployment files..."
FILES=(
    "Dockerfile.backend"
    "web/Dockerfile"
    "docker-compose.yml"
    "nginx/regimeflex.conf"
    "systemd/regimeflex.service"
    "deploy.sh"
    "rollback.sh"
    "setup-droplet.sh"
    "DEPLOYMENT.md"
    ".dockerignore"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        pass "File exists: $file"
    else
        fail "File missing: $file"
    fi
done

echo ""

# Check .env
echo "Checking environment configuration..."
if [ -f ".env" ]; then
    if grep -q "ALPACA_KEY=" .env && ! grep -q "ALPACA_KEY=your_" .env; then
        pass ".env file configured"
    else
        warn ".env file exists but may need API keys"
    fi
else
    if [ -f "env.example" ]; then
        warn ".env file not found (copy from env.example)"
    else
        fail ".env.example not found"
    fi
fi

echo ""

# Check health endpoints exist
echo "Checking health endpoints..."
if [ -f "regimeflex/scripts/run_http_trigger.py" ]; then
    if grep -q "@app.route(\"/health\"" regimeflex/scripts/run_http_trigger.py; then
        pass "Backend health endpoint exists"
    else
        fail "Backend health endpoint not found"
    fi
else
    warn "Backend file not found (may be in different location)"
fi

if [ -f "web/app/api/health/route.ts" ]; then
    pass "Frontend health endpoint exists"
else
    fail "Frontend health endpoint not found"
fi

echo ""

# Test Docker build (optional, takes time)
if [ "${1:-}" = "--build" ]; then
    echo "Testing Docker builds (this may take several minutes)..."
    
    echo "Building backend..."
    if docker build -f Dockerfile.backend -t regimeflex-backend-test . > /tmp/backend_build.log 2>&1; then
        pass "Backend Docker build successful"
    else
        fail "Backend Docker build failed (see /tmp/backend_build.log)"
    fi
    
    echo "Building frontend..."
    if docker build -f web/Dockerfile -t regimeflex-frontend-test ./web > /tmp/frontend_build.log 2>&1; then
        pass "Frontend Docker build successful"
    else
        fail "Frontend Docker build failed (see /tmp/frontend_build.log)"
    fi
fi

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Ensure .env is configured with API keys"
    echo "2. Run: ./deploy.sh YOUR_DROPLET_IP regimeflex"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please fix issues before deploying.${NC}"
    exit 1
fi

