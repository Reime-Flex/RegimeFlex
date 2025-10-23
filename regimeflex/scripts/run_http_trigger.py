import os
import sys
from pathlib import Path
from flask import Flask, jsonify

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.killswitch import is_killed
from engine.runner import run_daily_offline
from engine.config import Config
from engine.health import run_health

app = Flask(__name__)

@app.route("/trigger-daily", methods=["GET"])
def trigger_daily():
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
    return {"status": "ok", "timestamp": "2025-10-23T07:52:00Z"}, 200

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

if __name__ == "__main__":
    # IMPORTANT: bind to 0.0.0.0 and the PORT env var for Railway
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
