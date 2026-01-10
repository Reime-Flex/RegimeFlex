#!/bin/bash
# Test HTTP Server Locally
# This starts the HTTP server and tests all endpoints

set -e

echo "=========================================="
echo "RegimeFlex HTTP Server Test"
echo "=========================================="
echo ""

PORT=${PORT:-5000}
BASE_URL="http://localhost:${PORT}"

# Start server in background
echo "Starting HTTP server on port ${PORT}..."
python3 -m regimeflex http > /tmp/regimeflex_http_test.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start. Check logs:"
    cat /tmp/regimeflex_http_test.log
    exit 1
fi

echo "✅ Server started (PID: $SERVER_PID)"
echo ""

# Test endpoints
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    echo "Testing: $description"
    response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}" 2>/dev/null || echo -e "\n000")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo "  ✅ Status: $http_code (expected $expected_status)"
        if [ -n "$body" ]; then
            echo "  Response: $(echo "$body" | head -c 100)..."
        fi
    else
        echo "  ❌ Status: $http_code (expected $expected_status)"
        echo "  Response: $body"
    fi
    echo ""
}

# Test endpoints
test_endpoint "/health" "200" "Health check endpoint"
test_endpoint "/status" "200" "Status endpoint"
test_endpoint "/replay/latest" "200" "Replay latest endpoint (may return 404 if no replays)"
test_endpoint "/incidents" "200" "Incidents endpoint"

# Test trigger-daily (should return 200 or 423 if kill switch is active)
echo "Testing: Trigger daily endpoint"
response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/trigger-daily" 2>/dev/null || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ] || [ "$http_code" = "423" ]; then
    echo "  ✅ Status: $http_code (200=ok, 423=kill switch active)"
else
    echo "  ⚠️  Status: $http_code (unexpected, but may be ok)"
fi
echo ""

# Stop server
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "HTTP Server Test Complete"
echo "=========================================="
echo ""
echo "Server logs:"
echo "------------"
tail -20 /tmp/regimeflex_http_test.log || echo "No logs"

