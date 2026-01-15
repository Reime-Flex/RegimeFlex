"""
RegimeFlex HTTP Trigger Server

This Flask application provides HTTP endpoints for triggering the trading system.
Designed for Railway deployment and PM2 production execution.

PRODUCTION EXECUTION RULE:
This module MUST be executed as a package component:
    python -m regimeflex http

It MUST NOT be executed directly as a script:
    python regimeflex/scripts/run_http_trigger.py  # ❌ NOT SUPPORTED

This ensures proper package context and enables all relative imports
throughout the regimeflex package tree.

All imports use absolute imports from the regimeflex package root.
"""

import os
import sys
import json
import queue
import threading
from datetime import datetime, timezone
from flask import Flask, jsonify, Response

# CORS support (optional - only import if available)
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# Production rule: Always use absolute imports from regimeflex package
# These imports assume the module is executed within the package context
# (i.e., via 'python -m regimeflex http' or 'python -m regimeflex.scripts.run_http_trigger')
from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.killswitch import is_killed
from regimeflex.engine.runner import run_daily_offline
from regimeflex.engine.config import Config
from regimeflex.engine.health import run_health
from regimeflex.scripts.path_utils import detect_project_root, find_replay_directory, find_incidents_file
from regimeflex.scripts.replay_utils import load_latest_replay_from_dir
from regimeflex.config.paths import PROJECT_ROOT

# Market data and indicators for trading terminal
from regimeflex.engine.market_data import (
    fetch_latest_quote,
    fetch_latest_trade,
    fetch_snapshot,
    fetch_multi_snapshot,
    fetch_intraday_bars,
    fetch_account,
    fetch_positions,
    bars_to_dataframe,
)
from regimeflex.engine.indicators import compute_all_indicators

app = Flask(__name__)

# Enable CORS if available (for frontend-backend separation)
if CORS_AVAILABLE:
    CORS(app)
else:
    # Manual CORS headers if flask-cors not installed
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response

@app.route("/trigger-daily", methods=["GET"])
def trigger_daily():
    # Check if this is a health check (no query params, simple GET)
    import flask
    if not flask.request.args and flask.request.method == "GET":
        # Simple health check - just return OK without running the full cycle
        return jsonify({"status": "ok", "health_check": True}), 200

    # Require token for actual trigger (security: prevent unauthorized trades)
    expected_token = os.environ.get("TRIGGER_TOKEN")
    provided_token = flask.request.args.get("token")

    if expected_token and provided_token != expected_token:
        RF.print_log("Unauthorized trigger attempt - invalid token", "SECURITY")
        return jsonify({"status": "unauthorized", "error": "Invalid or missing token"}), 401

    if is_killed():
        RF.print_log("KILL-SWITCH active — refusing HTTP trigger", "RISK")
        return jsonify({"status": "killed"}), 423  # 423 = Locked
    cfg = Config(PROJECT_ROOT)
    run = cfg.run or {}
    result = run_daily_offline(
        equity=float(run.get("equity", 25000)),
        vix=run.get("vix_assumption", 20.0),
        minutes_to_close=int(run.get("minutes_to_close", 28)),
        min_trade_value=float(run.get("min_trade_value", 200.0))
    )
    RF.print_log("HTTP trigger completed.", "SUCCESS")
    return jsonify({"status": "ok", "result": {"target": result.get("target", {})}}), 200

@app.route("/health", methods=["GET"])
def health():
    # Simple health check for Railway - just return OK to avoid timeout issues
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}), 200

@app.route("/health-full", methods=["GET"])
def health_full():
    # Full health check for detailed diagnostics
    rep = run_health()
    code = 200 if rep.status == "PASS" else (429 if rep.status == "WARN" else 503)
    return jsonify({
        "status": rep.status,
        "timestamp": rep.timestamp,
        "checks": [c.__dict__ for c in rep.checks]
    }), code

@app.route("/replay/latest", methods=["GET"])
def replay_latest():
    """Return latest replay pack for frontend."""
    try:
        project_root, _ = detect_project_root()
        replay_dir = find_replay_directory(project_root)

        if not replay_dir:
            RF.print_log(f"No replay directory found. Checked: {project_root}", "WARNING")
            return jsonify({"found": False, "error": "No replay directory found"}), 404

        replay_data = load_latest_replay_from_dir(replay_dir)

        if not replay_data:
            RF.print_log(f"No replay files found in {replay_dir}", "WARNING")
            return jsonify({"found": False, "error": "No replay files found"}), 404

        RF.print_log(f"Loading replay from {replay_data.get('_path')}", "INFO")

        return jsonify({
            "found": True,
            "replay": replay_data
        }), 200

    except Exception as e:
        RF.print_log(f"Replay latest endpoint error: {e}", "ERROR")
        return jsonify({"found": False, "error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    """Return system status."""
    try:
        status_data = {
            "status": "active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kill_switch": is_killed()
        }
        return jsonify(status_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/incidents", methods=["GET"])
def incidents():
    """Return recent incidents."""
    try:
        project_root, _ = detect_project_root()
        incidents_file = find_incidents_file(project_root)

        if not incidents_file:
            return jsonify({"count": 0, "items": []}), 200

        incidents = []
        try:
            with open(incidents_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-20:]:  # Last 20
                    line = line.strip()
                    if line:
                        try:
                            incidents.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            RF.print_log(f"Error reading incidents: {e}", "WARNING")
        
        return jsonify({
            "count": len(incidents),
            "items": incidents
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Trading Terminal API Endpoints
# ============================================================================

@app.route("/bars/<symbol>", methods=["GET"])
def bars(symbol: str):
    """
    Fetch OHLCV bars for a symbol.

    Query params:
        tf: Timeframe - "1Min", "5Min", "15Min", "1Hour", "1Day" (default: "5Min")
        limit: Number of bars (default: 100, max: 1000)

    Returns:
        {
            "symbol": "TQQQ",
            "timeframe": "5Min",
            "bars": [
                {"t": "2024-01-14T15:30:00Z", "o": 78.40, "h": 78.50, "l": 78.35, "c": 78.45, "v": 1000},
                ...
            ]
        }
    """
    import flask
    try:
        timeframe = flask.request.args.get("tf", "5Min")
        limit = min(int(flask.request.args.get("limit", 100)), 1000)

        # Validate timeframe
        valid_timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
        if timeframe not in valid_timeframes:
            return jsonify({"error": f"Invalid timeframe. Use one of: {valid_timeframes}"}), 400

        bars_data = fetch_intraday_bars(symbol.upper(), timeframe=timeframe, limit=limit)

        if bars_data is None:
            return jsonify({"error": f"Failed to fetch bars for {symbol}"}), 500

        # Return empty array if no bars (market closed, etc.)
        return jsonify({
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "count": len(bars_data),
            "bars": bars_data,
            "note": "No data available (market may be closed)" if len(bars_data) == 0 else None
        }), 200

    except Exception as e:
        RF.print_log(f"Bars endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/quote/<symbol>", methods=["GET"])
def quote(symbol: str):
    """
    Fetch real-time quote for a symbol.

    Returns:
        {
            "symbol": "TQQQ",
            "last": 78.45,
            "bid": 78.44,
            "ask": 78.46,
            "change": 1.23,
            "change_pct": 1.59,
            "volume": 12345678,
            "timestamp": "2024-01-14T15:30:00Z"
        }
    """
    try:
        # Use snapshot for richer data (includes daily bar info)
        snapshot = fetch_snapshot(symbol.upper())

        if snapshot is None:
            # Fallback to basic quote + trade
            quote_data = fetch_latest_quote(symbol.upper())
            trade_data = fetch_latest_trade(symbol.upper())

            if quote_data is None and trade_data is None:
                return jsonify({"error": f"Failed to fetch quote for {symbol}"}), 500

            return jsonify({
                "symbol": symbol.upper(),
                "last": trade_data.get("price") if trade_data else None,
                "bid": quote_data.get("bid") if quote_data else None,
                "ask": quote_data.get("ask") if quote_data else None,
                "timestamp": trade_data.get("timestamp") if trade_data else None
            }), 200

        return jsonify(snapshot), 200

    except Exception as e:
        RF.print_log(f"Quote endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/quotes", methods=["GET"])
def quotes():
    """
    Fetch quotes for multiple symbols.

    Query params:
        symbols: Comma-separated list (e.g., "TQQQ,SQQQ,QQQ,SPY,VIX")

    Returns:
        {
            "TQQQ": {...},
            "SQQQ": {...},
            ...
        }
    """
    import flask
    try:
        symbols_param = flask.request.args.get("symbols", "TQQQ,SQQQ,QQQ,SPY")
        symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]

        if not symbols:
            return jsonify({"error": "No symbols provided"}), 400

        if len(symbols) > 10:
            return jsonify({"error": "Maximum 10 symbols allowed"}), 400

        snapshots = fetch_multi_snapshot(symbols)

        return jsonify(snapshots), 200

    except Exception as e:
        RF.print_log(f"Quotes endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/indicators/<symbol>", methods=["GET"])
def indicators(symbol: str):
    """
    Compute technical indicators for a symbol.

    Query params:
        tf: Timeframe for indicator calculation (default: "1Day")
        limit: Number of bars to use (default: 200)

    Returns:
        {
            "symbol": "TQQQ",
            "indicators": {
                "rsi": 65.4,
                "macd": 0.42,
                "macd_signal": 0.38,
                "macd_histogram": 0.04,
                "bb_upper": 82.50,
                "bb_middle": 78.00,
                "bb_lower": 73.50,
                "atr": 2.34,
                "sma_20": 77.80,
                "sma_50": 75.20,
                "sma_200": 68.50
            }
        }
    """
    import flask
    try:
        timeframe = flask.request.args.get("tf", "1Day")
        limit = min(int(flask.request.args.get("limit", 200)), 500)

        # Fetch bars
        bars_data = fetch_intraday_bars(symbol.upper(), timeframe=timeframe, limit=limit)

        if bars_data is None or len(bars_data) < 30:
            return jsonify({
                "symbol": symbol.upper(),
                "indicators": {},
                "error": "Insufficient data for indicator calculation"
            }), 200

        # Convert to DataFrame
        df = bars_to_dataframe(bars_data)

        # Compute indicators
        indicators_data = compute_all_indicators(df)

        return jsonify({
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "bars_used": len(bars_data),
            "indicators": indicators_data
        }), 200

    except Exception as e:
        RF.print_log(f"Indicators endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/account", methods=["GET"])
def account():
    """
    Fetch Alpaca account information.

    Returns:
        {
            "equity": 100000.00,
            "cash": 50000.00,
            "buying_power": 200000.00,
            "portfolio_value": 100000.00,
            "day_pnl": 500.00,
            "day_pnl_pct": 0.50
        }
    """
    try:
        account_data = fetch_account()

        if account_data is None:
            return jsonify({"error": "Failed to fetch account data"}), 500

        return jsonify(account_data), 200

    except Exception as e:
        RF.print_log(f"Account endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/positions", methods=["GET"])
def positions():
    """
    Fetch current positions from Alpaca.

    Returns:
        {
            "count": 1,
            "positions": [
                {
                    "symbol": "TQQQ",
                    "qty": 100,
                    "side": "long",
                    "avg_entry": 78.00,
                    "current_price": 78.45,
                    "market_value": 7845.00,
                    "unrealized_pnl": 45.00,
                    "unrealized_pnl_pct": 0.58
                }
            ]
        }
    """
    try:
        positions_data = fetch_positions()

        return jsonify({
            "count": len(positions_data),
            "positions": positions_data
        }), 200

    except Exception as e:
        RF.print_log(f"Positions endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio", methods=["GET"])
def portfolio():
    """
    Combined endpoint for account + positions (reduces API calls from frontend).

    Returns:
        {
            "account": {...},
            "positions": [...],
            "timestamp": "2024-01-14T15:30:00Z"
        }
    """
    try:
        account_data = fetch_account()
        positions_data = fetch_positions()

        return jsonify({
            "account": account_data or {},
            "positions": positions_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        RF.print_log(f"Portfolio endpoint error: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Server-Sent Events (SSE) for Real-Time Updates
# ============================================================================

# Global list of SSE client queues
_sse_queues: list = []
_sse_lock = threading.Lock()

def broadcast_sse_event(event_type: str, data: dict) -> None:
    """
    Broadcast event to all connected SSE clients.

    Args:
        event_type: Event type (e.g., "trade_update", "position_update")
        data: Event data dictionary
    """
    event = {"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
    event_json = json.dumps(event)

    with _sse_lock:
        for q in _sse_queues:
            try:
                q.put_nowait(event_json)
            except queue.Full:
                pass  # Skip if queue is full


@app.route("/events", methods=["GET"])
def sse_events():
    """
    Server-Sent Events endpoint for real-time updates.

    Event types:
    - trade_update: Fill/cancel/reject events from Alpaca
    - position_update: Position changes
    - regime_update: Regime state changes
    - connection_status: WebSocket connection status

    Usage (JavaScript):
        const eventSource = new EventSource('/events');
        eventSource.addEventListener('trade_update', (e) => {
            const data = JSON.parse(e.data);
            console.log('Trade update:', data);
        });
    """
    def generate():
        # Create queue for this client
        client_queue = queue.Queue(maxsize=100)

        with _sse_lock:
            _sse_queues.append(client_queue)

        RF.print_log(f"[SSE] Client connected ({len(_sse_queues)} total)", "INFO")

        try:
            # Send initial connection event
            yield f"event: connection_status\ndata: {json.dumps({'status': 'connected'})}\n\n"

            while True:
                try:
                    # Wait for events with timeout for keepalive
                    event_json = client_queue.get(timeout=30)
                    event_data = json.loads(event_json)
                    event_type = event_data.get("type", "message")
                    yield f"event: {event_type}\ndata: {event_json}\n\n"

                except queue.Empty:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        except GeneratorExit:
            RF.print_log("[SSE] Client disconnected", "INFO")
        finally:
            with _sse_lock:
                if client_queue in _sse_queues:
                    _sse_queues.remove(client_queue)
            RF.print_log(f"[SSE] Client removed ({len(_sse_queues)} remaining)", "INFO")

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.route("/events/broadcast", methods=["POST"])
def broadcast_event():
    """
    Manually broadcast an event to all SSE clients.
    Used for testing or manual notifications.

    Body:
        {"type": "test", "data": {"message": "Hello"}}
    """
    import flask
    try:
        body = flask.request.get_json() or {}
        event_type = body.get("type", "message")
        data = body.get("data", {})

        broadcast_sse_event(event_type, data)

        return jsonify({"status": "ok", "clients": len(_sse_queues)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Global stream manager reference
_stream_manager = None
_stream_thread = None

def init_streaming():
    """Initialize WebSocket streaming in background."""
    global _stream_manager, _stream_thread

    try:
        from regimeflex.engine.realtime.stream_manager import StreamManager, start_stream_background

        # Start stream manager
        _stream_thread = start_stream_background()

        # Get instance and subscribe to events
        _stream_manager = StreamManager.get_instance()
        _stream_manager.subscribe(lambda event: broadcast_sse_event(event.event_type, event.data))

        RF.print_log("[SSE] Stream manager initialized and connected to SSE", "SUCCESS")
        return True

    except ImportError as e:
        RF.print_log(f"[SSE] Stream manager not available: {e}", "RISK")
        return False
    except Exception as e:
        RF.print_log(f"[SSE] Failed to initialize streaming: {e}", "ERROR")
        return False


def main():
    """
    Main entrypoint for HTTP server.

    This function is called by:
    - python -m regimeflex http (via __main__.py routing)
    - python -m regimeflex.scripts.run_http_trigger (direct module execution)

    It MUST NOT be called by direct script execution.
    """
    # IMPORTANT: bind to 0.0.0.0 and the PORT env var for Railway/PM2
    port = int(os.environ.get("PORT", "5000"))

    # Initialize real-time streaming (optional, non-blocking)
    enable_streaming = os.environ.get("ENABLE_STREAMING", "false").lower() == "true"
    if enable_streaming:
        RF.print_log("Initializing real-time streaming...", "INFO")
        init_streaming()
    else:
        RF.print_log("Real-time streaming disabled (set ENABLE_STREAMING=true to enable)", "INFO")

    RF.print_log(f"Starting HTTP server on 0.0.0.0:{port}", "INFO")
    app.run(host="0.0.0.0", port=port, debug=False)

# Production rule: Prevent direct script execution
# This module must be run as a package component to ensure proper import context
if __name__ == "__main__":
    RF.print_log(
        "ERROR: This module must be executed as a package component.\n"
        "  Use: python -m regimeflex http\n"
        "  NOT: python regimeflex/scripts/run_http_trigger.py",
        "ERROR"
    )
    sys.exit(1)
