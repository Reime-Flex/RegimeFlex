#!/usr/bin/env python
from __future__ import annotations

import os
import subprocess
import sys
import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds
from engine.incident import IncidentLogger

TOKEN_ENV = "REGIMEFLEX_TRIGGER_TOKEN"


def get_lock_path(root: Path, lock_name: str) -> Path:
    """Get the lock file path relative to the given root."""
    return root / "logs" / "locks" / lock_name


def ensure_lock_dir(path: Path):
    """Ensure lock directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def lock_is_active(path: Path, max_age_seconds: int = 60 * 30) -> bool:
    """
    Return True if lock exists and is recent.
    max_age_seconds prevents permanent lock if a process crashes.
    """
    if not path.exists():
        return False
    try:
        age = time.time() - path.stat().st_mtime
        return age < max_age_seconds
    except Exception:
        # If we can't stat the file, assume it's not active
        return False


def acquire_lock(path: Path):
    """Create lock file with current timestamp."""
    ensure_lock_dir(path)
    path.write_text(str(int(time.time())), encoding="utf-8")


def release_lock(path: Path):
    """Remove lock file if it exists."""
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def run_cmd(cmd, cwd=None):
    """Run a command and return exit code."""
    try:
        p = subprocess.run(cmd, cwd=cwd)
        return int(p.returncode)
    except Exception:
        return 1


def get_receipt(root: Path, make_cwd: Path):
    """Get receipt data by running run_receipt.py."""
    try:
        # The script is always in regimeflex/scripts/run_receipt.py
        # root is the regimeflex directory, make_cwd is where make runs from
        script_path = root / "scripts" / "run_receipt.py"
        
        if not script_path.exists():
            RF.print_log(f"Receipt script not found at {script_path}", "WARNING")
            return {}
        
        # Run from the make_cwd (project root) so paths resolve correctly
        out = subprocess.check_output(
            [sys.executable, str(script_path)],
            cwd=str(make_cwd),
            text=True
        )
        return json.loads(out)
    except Exception as e:
        RF.print_log(f"Receipt generation failed: {e}", "WARNING")
        return {}


def get_next_run(root: Path, make_cwd: Path):
    """Get next run preview by running next_run_receipt.py."""
    try:
        # The script is always in regimeflex/scripts/next_run_receipt.py
        # root is the regimeflex directory, make_cwd is where make runs from
        script_path = root / "scripts" / "next_run_receipt.py"
        
        if not script_path.exists():
            RF.print_log(f"Next run receipt script not found at {script_path}", "WARNING")
            return {}
        
        # Run from the make_cwd (project root) so paths resolve correctly
        out = subprocess.check_output(
            [sys.executable, str(script_path)],
            cwd=str(make_cwd),
            text=True
        )
        return json.loads(out)
    except Exception as e:
        RF.print_log(f"Next run preview generation failed: {e}", "WARNING")
        return {}


def send_telegram_receipt(text: str, root: Path):
    """Best-effort Telegram send using existing Notifier class."""
    try:
        cfg = Config(root)
        tel_cfg = cfg._load_yaml("config/telemetry.yaml") if (cfg.root / "config/telemetry.yaml").exists() else {}
        if not tel_cfg.get("enabled", True):
            RF.print_log("Telemetry disabled; skipping receipt", "INFO")
            return
        
        env = load_env()
        notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
        notifier.send(text)
    except Exception as e:
        RF.print_log(f"Telegram receipt failed (non-blocking): {e}", "WARNING")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        token = (qs.get("token") or [""])[0]

        expected = os.environ.get(TOKEN_ENV, "")
        if not expected or token != expected:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if parsed.path not in ("/run", "/status", "/health", "/preflight", "/incidents", "/replay/latest"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        # Detect correct directory for make command and receipt
        cwd = Path(".")
        if (cwd / "regimeflex" / "config").exists():
            make_cwd = cwd
            root = cwd / "regimeflex"
        else:
            parent = cwd.parent
            if (parent / "regimeflex" / "config").exists():
                make_cwd = parent
                root = parent / "regimeflex"
            else:
                make_cwd = cwd
                root = cwd

        # Handle /status endpoint (read-only, no execution)
        if parsed.path == "/status":
            receipt = get_receipt(root, make_cwd)
            next_run = get_next_run(root, make_cwd)
            payload = {
                "outcome": "STATUS_ONLY",
                "receipt": receipt,
                "next_run": next_run,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            return

        # Handle /incidents endpoint (read-only, no execution)
        if parsed.path == "/incidents":
            day = (qs.get("day") or [""])[0].strip() or None
            limit_raw = (qs.get("limit") or ["20"])[0].strip() or "20"
            try:
                limit = int(limit_raw)
            except Exception:
                limit = 20

            try:
                # The script is always in regimeflex/scripts/incidents_tail.py
                script_path = root / "scripts" / "incidents_tail.py"
                
                if not script_path.exists():
                    RF.print_log(f"Incidents tail script not found at {script_path}", "WARNING")
                    payload = {"day": day, "limit": limit, "count": 0, "items": []}
                else:
                    # Run from the make_cwd (project root) so paths resolve correctly
                    day_arg = f"--day={day}" if day else "--day="
                    out = subprocess.check_output(
                        [sys.executable, str(script_path), day_arg, f"--limit={limit}"],
                        cwd=str(make_cwd),
                        text=True
                    )
                    payload = json.loads(out)
            except Exception as e:
                RF.print_log(f"Incidents tail generation failed: {e}", "WARNING")
                payload = {"day": day, "limit": limit, "count": 0, "items": []}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            return

        # Handle /replay/latest endpoint (read-only, no execution)
        if parsed.path == "/replay/latest":
            mode = (qs.get("mode") or ["summary"])[0].strip() or "summary"
            if mode not in ("summary", "full"):
                mode = "summary"

            try:
                # The script is always in regimeflex/scripts/replay_latest_receipt.py
                script_path = root / "scripts" / "replay_latest_receipt.py"
                
                if not script_path.exists():
                    RF.print_log(f"Replay latest receipt script not found at {script_path}", "WARNING")
                    payload = {"found": False}
                else:
                    # Run from the make_cwd (project root) so paths resolve correctly
                    out = subprocess.check_output(
                        [sys.executable, str(script_path), f"--mode={mode}"],
                        cwd=str(make_cwd),
                        text=True
                    )
                    payload = json.loads(out)
            except Exception as e:
                RF.print_log(f"Replay latest generation failed: {e}", "WARNING")
                payload = {"found": False}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            return

        # Handle /health endpoint (runs make health only)
        if parsed.path == "/health":
            health_lock = get_lock_path(make_cwd, "trigger_health.lock")
            
            # Prevent overlapping /health executions
            if lock_is_active(health_lock, max_age_seconds=60 * 10):
                payload = {
                    "outcome": "BUSY",
                    "message": "A health check is already in progress.",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
                self.send_response(409)  # Conflict
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
                return

            acquire_lock(health_lock)
            try:
                rc = run_cmd(["make", "health"], cwd=str(make_cwd))
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "pass": (rc == 0),
                    "rc": rc,
                }

                # If health fails, log an incident (best effort; does not break endpoint)
                if rc != 0:
                    try:
                        # Use make_cwd (project root) for incident logging so logs go to the right place
                        incidents = IncidentLogger(root=make_cwd)
                        incidents.log(
                            "WARNING",
                            "Remote /health endpoint detected failing health check",
                            {"rc": rc}
                        )
                    except Exception as e:
                        RF.print_log(f"Incident logging failed (non-blocking): {e}", "WARNING")

                self.send_response(200 if rc == 0 else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            finally:
                release_lock(health_lock)
            return

        # Handle /preflight endpoint (runs make preflight only)
        if parsed.path == "/preflight":
            preflight_lock = get_lock_path(make_cwd, "trigger_preflight.lock")
            
            # Prevent overlapping /preflight executions
            if lock_is_active(preflight_lock, max_age_seconds=60 * 30):
                payload = {
                    "outcome": "BUSY",
                    "message": "A preflight is already in progress.",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
                self.send_response(409)  # Conflict
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
                return

            acquire_lock(preflight_lock)
            try:
                rc = run_cmd(["make", "preflight"], cwd=str(make_cwd))
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "pass": (rc == 0),
                    "rc": rc,
                }

                # If preflight fails, log incident + send Telegram (best-effort)
                if rc != 0:
                    try:
                        # Use make_cwd (project root) for incident logging so logs go to the right place
                        incidents = IncidentLogger(root=make_cwd)
                        incidents.log(
                            "CRITICAL",
                            "Remote /preflight endpoint detected failing preflight",
                            {"rc": rc}
                        )
                    except Exception as e:
                        RF.print_log(f"Incident logging failed (non-blocking): {e}", "WARNING")

                    # Telegram on failure only (best effort)
                    try:
                        msg = "🚨 *RegimeFlex ALERT*\n/preflight failed via remote endpoint. Trading should not run."
                        send_telegram_receipt(msg, root)
                    except Exception as e:
                        RF.print_log(f"Telegram alert failed (non-blocking): {e}", "WARNING")

                self.send_response(200 if rc == 0 else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            finally:
                release_lock(preflight_lock)
            return
        
        # Handle /run endpoint (executes gated-live)
        run_lock = get_lock_path(make_cwd, "trigger_run.lock")
        
        # Prevent overlapping /run executions
        if lock_is_active(run_lock, max_age_seconds=60 * 60):
            payload = {
                "outcome": "BUSY",
                "message": "A run is already in progress (lock active). Try again later.",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            self.send_response(409)  # Conflict
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
            return

        # Acquire lock and execute run
        acquire_lock(run_lock)
        try:
            # Run gated-live
            print(RF.formatted_log("Trigger received: running make gated-live", "INFO"))
            rc = run_cmd(["make", "gated-live"], cwd=str(make_cwd))

            # Get receipt metadata
            receipt = get_receipt(root, make_cwd)

            # Decide outcome label
            if rc == 0:
                outcome = "OK"
            else:
                # We can distinguish blocked vs failed by looking at receipt no_op + reason,
                # but we won't assume; we'll just mark FAILED and include no_op fields if present.
                outcome = "FAILED"

            payload = {
                "outcome": outcome,
                "rc": rc,
                "receipt": receipt,
            }

            # Telegram message (always)
            as_of = receipt.get("as_of") or "N/A"
            mode = (receipt.get("execution_mode") or {})
            mode_label = "DRY-RUN" if mode.get("dry_run") else "LIVE"
            mode_src = mode.get("source", "none")

            no_op = receipt.get("no_op")
            no_op_reason = receipt.get("no_op_reason") or ""

            msg = f"*RegimeFlex Trigger Receipt*\nOutcome: {outcome}\nAs-of: {as_of}\nMode: {mode_label} (source: {mode_src})"
            if no_op:
                msg += f"\nNo-op: True\nReason: {no_op_reason}"

            send_telegram_receipt(msg, root)

            # HTTP response
            self.send_response(200 if rc == 0 else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))
        finally:
            release_lock(run_lock)
        return

    def log_message(self, fmt, *args):
        # Keep HTTP server logs quiet
        return


def main():
    port = int(os.environ.get("REGIMEFLEX_TRIGGER_PORT", "8080"))
    host = os.environ.get("REGIMEFLEX_TRIGGER_HOST", "0.0.0.0")
    srv = HTTPServer((host, port), Handler)
    print(RF.formatted_log(f"Trigger server listening on http://{host}:{port}", "INFO"))
    print(RF.formatted_log(f"Endpoints: /run (execute), /status (read-only), /health (health check), /preflight (preflight check), /incidents (read-only), /replay/latest (read-only)", "INFO"))
    print(RF.formatted_log(f"Set REGIMEFLEX_TRIGGER_TOKEN environment variable to secure endpoints", "INFO"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print(RF.formatted_log("Trigger server stopped", "INFO"))
        srv.shutdown()


if __name__ == "__main__":
    main()

