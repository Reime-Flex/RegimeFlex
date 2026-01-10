#!/bin/bash
# Quick script to check PM2 configuration

echo "=== PM2 Configuration Check ==="
echo ""

# Check if ecosystem.local.config.js exists
if [ -f "ecosystem.local.config.js" ]; then
    echo "✅ ecosystem.local.config.js exists"
    echo ""
    echo "Current configuration:"
    grep -A 5 '"name": "regimeflex"' ecosystem.local.config.js | head -10
else
    echo "❌ ecosystem.local.config.js NOT FOUND"
    echo "Creating from template..."
fi

echo ""
echo "=== Key Checks ==="
echo ""

# Check if using module execution
if grep -q '"-m regimeflex http"' ecosystem.local.config.js 2>/dev/null; then
    echo "✅ Using module execution (-m regimeflex http)"
else
    echo "❌ NOT using module execution - this will cause ImportError!"
    echo "   Should be: args: \"-m regimeflex http\""
fi

# Check if using venv Python
if grep -q '\.venv312/bin/python' ecosystem.local.config.js 2>/dev/null; then
    echo "✅ Using venv Python (.venv312/bin/python)"
else
    echo "⚠️  Not explicitly using venv Python"
    echo "   Consider adding: interpreter: \".venv312/bin/python\""
fi

echo ""
echo "=== Next Steps ==="
echo "1. Check PM2 logs: pm2 logs regimeflex --lines 50"
echo "2. Verify Python works: .venv312/bin/python -m regimeflex --help"
echo "3. Update ecosystem.local.config.js with correct paths"
