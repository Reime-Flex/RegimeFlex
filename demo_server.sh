#!/bin/bash
# Interactive Demo Script for RegimeFlex HTTP Server

PORT=${PORT:-5000}
BASE_URL="http://localhost:${PORT}"

echo "=========================================="
echo "RegimeFlex HTTP Server Demo"
echo "=========================================="
echo ""
echo "Starting server on port ${PORT}..."
echo ""

# Start server in background
python3 -m regimeflex http > /tmp/regimeflex_demo.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
for i in {1..5}; do
    if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
        echo "✅ Server is running!"
        break
    fi
    sleep 1
done

if ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo "❌ Server failed to start. Check logs:"
    cat /tmp/regimeflex_demo.log
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo ""
echo "Server PID: $SERVER_PID"
echo "Logs: /tmp/regimeflex_demo.log"
echo ""
echo "=========================================="
echo "Testing Endpoints"
echo "=========================================="
echo ""

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local name=$2
    
    echo "📍 $name"
    echo "   GET ${BASE_URL}${endpoint}"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}${endpoint}")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    echo "   Status: $http_code"
    if [ -n "$body" ] && [ "$body" != "null" ]; then
        echo "$body" | python3 -m json.tool 2>/dev/null | head -15 | sed 's/^/   /' || echo "   $body" | head -5 | sed 's/^/   /'
    fi
    echo ""
}

# Test all endpoints
test_endpoint "/health" "Health Check"
test_endpoint "/status" "System Status"
test_endpoint "/replay/latest" "Latest Replay"
test_endpoint "/incidents" "Recent Incidents"

echo "=========================================="
echo "Server is running!"
echo "=========================================="
echo ""
echo "Commands:"
echo "  View logs:     tail -f /tmp/regimeflex_demo.log"
echo "  Stop server:   kill $SERVER_PID"
echo "  Test health:   curl ${BASE_URL}/health"
echo "  Test status:   curl ${BASE_URL}/status"
echo ""
echo "Press Ctrl+C to stop the server..."
echo ""

# Keep script running and show logs
tail -f /tmp/regimeflex_demo.log &
TAIL_PID=$!

# Trap Ctrl+C
trap "echo ''; echo 'Stopping server...'; kill $SERVER_PID $TAIL_PID 2>/dev/null; exit" INT

# Wait for server
wait $SERVER_PID

