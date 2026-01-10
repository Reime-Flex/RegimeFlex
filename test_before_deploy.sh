#!/bin/bash
# Pre-Deployment Testing Script for RegimeFlex
# Run this before deploying to VPS to ensure everything works

set -e  # Exit on error

echo "=========================================="
echo "RegimeFlex Pre-Deployment Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

test_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
}

echo "1. Testing Python Environment"
echo "----------------------------"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "Python: $PYTHON_VERSION"
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
        test_pass "Python version >= 3.12"
    else
        test_fail "Python version < 3.12 (required: 3.12+)"
    fi
else
    test_fail "python3 not found"
fi
echo ""

echo "2. Testing Package Structure"
echo "----------------------------"
if [ -f "regimeflex/__init__.py" ]; then
    test_pass "regimeflex/__init__.py exists"
else
    test_fail "regimeflex/__init__.py missing"
fi

if [ -f "regimeflex/engine/__init__.py" ]; then
    test_pass "regimeflex/engine/__init__.py exists"
else
    test_fail "regimeflex/engine/__init__.py missing"
fi

if [ -f "regimeflex/scripts/run_http_trigger.py" ]; then
    test_pass "run_http_trigger.py exists"
else
    test_fail "run_http_trigger.py missing"
fi
echo ""

echo "3. Testing Absolute Imports"
echo "----------------------------"
python3 << 'PYTEST'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))

try:
    from regimeflex.engine.runner import run_daily_offline, main
    print("✅ PASS: runner.py imports work")
except ImportError as e:
    print(f"❌ FAIL: runner.py import failed: {e}")
    sys.exit(1)

try:
    from regimeflex.scripts.run_http_trigger import app, main
    print("✅ PASS: run_http_trigger.py imports work")
except ImportError as e:
    print(f"❌ FAIL: run_http_trigger.py import failed: {e}")
    sys.exit(1)

try:
    from regimeflex.engine.identity import RegimeFlexIdentity
    print("✅ PASS: identity.py imports work")
except ImportError as e:
    print(f"❌ FAIL: identity.py import failed: {e}")
    sys.exit(1)
PYTEST

if [ $? -eq 0 ]; then
    test_pass "All critical imports work"
else
    test_fail "Import tests failed"
fi
echo ""

echo "4. Testing Module Execution"
echo "----------------------------"
# Test python -m regimeflex --help
if python3 -m regimeflex --help &> /dev/null; then
    test_pass "python -m regimeflex --help works"
else
    test_fail "python -m regimeflex --help failed"
fi

# Test python -m regimeflex.engine.runner (should fail gracefully without config)
if timeout 5 python3 -m regimeflex.engine.runner 2>&1 | grep -q "Missing config\|Config params\|Daily cycle"; then
    test_pass "python -m regimeflex.engine.runner executes (graceful failure expected)"
else
    test_warn "python -m regimeflex.engine.runner may have issues (check manually)"
fi
echo ""

echo "5. Testing HTTP Server Startup"
echo "-------------------------------"
# Start server in background, test it, then kill it
SERVER_PID=""
timeout 3 python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))
from regimeflex.scripts.run_http_trigger import app
print('✅ HTTP server imports successfully')
" 2>&1

if [ $? -eq 0 ]; then
    test_pass "HTTP server can be imported"
else
    test_fail "HTTP server import failed"
fi

# Test that Flask app exists
python3 << 'PYTEST'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))
from regimeflex.scripts.run_http_trigger import app
if app is not None:
    print("✅ Flask app object exists")
else:
    print("❌ Flask app object is None")
    sys.exit(1)
PYTEST

if [ $? -eq 0 ]; then
    test_pass "Flask app object exists"
else
    test_fail "Flask app object missing"
fi
echo ""

echo "6. Testing Configuration Files"
echo "-------------------------------"
if [ -d "regimeflex/config" ]; then
    test_pass "config/ directory exists"
    
    REQUIRED_CONFIGS=("run.yaml" "risk.yaml" "exposure.yaml" "broker.yaml")
    for config in "${REQUIRED_CONFIGS[@]}"; do
        if [ -f "regimeflex/config/$config" ]; then
            test_pass "config/$config exists"
        else
            test_warn "config/$config missing (may be optional)"
        fi
    done
else
    test_fail "config/ directory missing"
fi
echo ""

echo "7. Testing Environment Setup"
echo "----------------------------"
if [ -f ".env" ] || [ -f "regimeflex/config/env.example" ]; then
    test_pass ".env or env.example exists"
    if [ -f ".env" ]; then
        test_warn ".env file found (ensure it's configured for production)"
    fi
else
    test_warn ".env file not found (create from env.example)"
fi

# Check if required env vars are documented
if grep -q "ALPACA_KEY\|POLYGON_KEY" .env.example 2>/dev/null || grep -q "ALPACA_KEY\|POLYGON_KEY" regimeflex/config/env.example 2>/dev/null; then
    test_pass "Environment variables documented"
else
    test_warn "Environment variables may not be documented"
fi
echo ""

echo "8. Testing Dependencies"
echo "-----------------------"
python3 << 'PYTEST'
import sys
required = [
    'flask',
    'pandas',
    'numpy',
    'yaml',
]

missing = []
for module in required:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f"❌ FAIL: Missing dependencies: {', '.join(missing)}")
    print("   Install with: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("✅ PASS: All required dependencies installed")
PYTEST

if [ $? -eq 0 ]; then
    test_pass "Dependencies check"
else
    test_fail "Missing dependencies"
fi
echo ""

echo "9. Testing PM2 Configuration"
echo "---------------------------"
if [ -f "ecosystem.config.js" ]; then
    test_pass "ecosystem.config.js exists"
    
    # Check if it uses module execution
    if grep -q '"-m regimeflex http"' ecosystem.config.js; then
        test_pass "PM2 config uses module execution (-m regimeflex http)"
    else
        test_fail "PM2 config does NOT use module execution (will cause import errors)"
    fi
else
    test_warn "ecosystem.config.js not found (create for PM2 deployment)"
fi
echo ""

echo "10. Testing Script Execution"
echo "----------------------------"
# Test that scripts can be run directly
python3 << 'PYTEST'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('regimeflex').resolve().parent))

# Test run_http_trigger.py can be imported as script
try:
    import importlib.util
    script_path = Path('regimeflex/scripts/run_http_trigger.py')
    spec = importlib.util.spec_from_file_location("test_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, 'app') and hasattr(module, 'main'):
        print("✅ PASS: Script can be executed directly")
    else:
        print("❌ FAIL: Script missing app or main")
        sys.exit(1)
except Exception as e:
    print(f"❌ FAIL: Script execution test failed: {e}")
    sys.exit(1)
PYTEST

if [ $? -eq 0 ]; then
    test_pass "Script execution test"
else
    test_fail "Script execution test failed"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Ready for deployment.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review any warnings above"
    echo "2. Test manually: python3 -m regimeflex http"
    echo "3. Deploy to VPS"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Fix issues before deploying.${NC}"
    exit 1
fi

