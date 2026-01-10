"""
RegimeFlex HTTP Trigger Server

This Flask application provides HTTP endpoints for triggering the trading system.
Designed for Railway deployment and cron-based execution.

Execution Context:
- Can be run directly: python regimeflex/scripts/run_http_trigger.py
- Can be run as module: python -m regimeflex http
- Can be run via entrypoint: python regimeflex_entrypoint.py http

All methods ensure proper package context for relative imports.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify

# CORS support (optional - only import if available)
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# Ensure proper package context
# Strategy: Detect if running as script or module, use appropriate imports
_regimeflex_dir = Path(__file__).parent.parent

# Check if we're running as a script (__name__ == "__main__" when imported as module)
# or if regimeflex is already in sys.path (module execution)
_is_module_context = "regimeflex" in sys.modules or (
    len(sys.path) > 0 and Path(sys.path[0]).resolve() == _regimeflex_dir.parent.resolve()
)

if not _is_module_context and str(_regimeflex_dir) not in sys.path:
    # Running as script - add regimeflex to path
    sys.path.insert(0, str(_regimeflex_dir))
    # Use absolute imports
    from engine.identity import RegimeFlexIdentity as RF
    from engine.killswitch import is_killed
    from engine.runner import run_daily_offline
    from engine.config import Config
    from engine.health import run_health
    from scripts.path_utils import detect_project_root, find_replay_directory, find_incidents_file
    from scripts.replay_utils import load_latest_replay
else:
    # Running as module - use relative imports
    from ..engine.identity import RegimeFlexIdentity as RF
    from ..engine.killswitch import is_killed
    from ..engine.runner import run_daily_offline
    from ..engine.config import Config
    from ..engine.health import run_health
    from .path_utils import detect_project_root, find_replay_directory, find_incidents_file
    from .replay_utils import load_latest_replay

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
    
    if is_killed():
        RF.print_log("KILL-SWITCH active — refusing HTTP trigger", "RISK")
        return jsonify({"status": "killed"}), 423  # 423 = Locked
    cfg = Config(".")
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
        project_root = detect_project_root()
        replay_dir = find_replay_directory(project_root)

        if not replay_dir:
            RF.print_log(f"No replay directory found. Checked: {project_root}", "WARNING")
            return jsonify({"found": False, "error": "No replay directory found"}), 404

        replay_data = load_latest_replay(replay_dir)

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
        project_root = detect_project_root()
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

def main():
    """Main entrypoint for HTTP server."""
    # IMPORTANT: bind to 0.0.0.0 and the PORT env var for Railway
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
