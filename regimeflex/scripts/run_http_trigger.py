import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify

# Add parent directory to path to import engine module
regimeflex_dir = Path(__file__).parent.parent
sys.path.insert(0, str(regimeflex_dir))

from engine.identity import RegimeFlexIdentity as RF
from engine.killswitch import is_killed
from engine.runner import run_daily_offline
from engine.config import Config
from engine.health import run_health

# Import path utilities (use absolute import since this is run as a script)
# When run directly, regimeflex_dir is in sys.path, so use 'scripts' prefix
from scripts.path_utils import detect_project_root, find_replay_directory, find_incidents_file
from scripts.replay_utils import load_latest_replay

app = Flask(__name__)

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
    return {
        "status": rep.status,
        "timestamp": rep.timestamp,
        "checks": [c.__dict__ for c in rep.checks]
    }, code

@app.route("/replay/latest", methods=["GET"])
def replay_latest():
    """Return latest replay pack for frontend."""
    try:
        # Use consolidated utility function
        replay_data = load_latest_replay()
        
        if not replay_data:
            RF.print_log("No replay files found", "WARNING")
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
        # Use consolidated utility function
        incidents_file = find_incidents_file()
        
        if not incidents_file:
            return jsonify({"count": 0, "items": []}), 200
        
        # Read last N incidents
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

if __name__ == "__main__":
    # IMPORTANT: bind to 0.0.0.0 and the PORT env var for Railway
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
