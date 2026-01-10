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
from datetime import datetime, timezone
from flask import Flask, jsonify

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
from regimeflex.scripts.replay_utils import load_latest_replay_from_dir_from_dir

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
