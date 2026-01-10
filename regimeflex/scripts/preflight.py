#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.incident import IncidentLogger
from engine.config import Config
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds


def run(cmd: list[str], label: str) -> int:
    print(RF.formatted_log(f"Running {label}: {' '.join(cmd)}", "INFO"))
    p = subprocess.run(cmd)
    return int(p.returncode)


def send_telegram_alert(message: str, root: Path, meta: dict | None = None) -> None:
    """Send Telegram alert (best-effort, fails silently if not configured)."""
    try:
        cfg = Config(root)
        tel_cfg = cfg._load_yaml("config/telemetry.yaml") if (cfg.root / "config/telemetry.yaml").exists() else {}
        if not tel_cfg.get("enabled", True):
            RF.print_log("Telemetry disabled; skipping alert", "INFO")
            return
        
        env = load_env()
        notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
        notifier.send(message)
    except Exception as e:
        RF.print_log(f"Telegram alert failed (non-blocking): {e}", "WARNING")


def main() -> int:
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        # We're at project root, use regimeflex as root
        root = cwd / "regimeflex"
        # Make commands should be run from project root
        make_cwd = cwd
    else:
        # We're in regimeflex directory
        root = cwd
        # Make commands should be run from parent (project root) if it exists
        parent = cwd.parent
        if (parent / "regimeflex" / "config").exists():
            make_cwd = parent
        else:
            make_cwd = cwd
    
    incidents = IncidentLogger(root=root)

    # Always rebuild status dashboard (even if health fails, we want the latest view)
    # But run health first so status includes the latest replay context from normal runs.
    # Run make commands from the correct directory (project root)
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(str(make_cwd))
        rc_health = run(["make", "health"], "health")
        rc_status = run(["make", "status"], "status")
    finally:
        os.chdir(original_cwd)

    # If status generation itself fails, treat as critical too
    if rc_status != 0:
        incidents.log(
            "CRITICAL",
            "Pre-flight failed: status dashboard generation failed",
            {"rc_status": rc_status}
        )
        send_telegram_alert(
            "🚨 *Pre-flight CRITICAL*\nStatus dashboard generation failed. Trading should not run.",
            root=root,
            meta={"rc_status": rc_status}
        )
        print(RF.formatted_log("Pre-flight: FAIL (status)", "ERROR"))
        return 1

    if rc_health != 0:
        incidents.log(
            "CRITICAL",
            "Pre-flight failed: health check failed",
            {"rc_health": rc_health}
        )

        # Telegram alert (best-effort)
        send_telegram_alert(
            "🚨 *Pre-flight CRITICAL*\nHealth check failed. Trading should not run.",
            root=root,
            meta={"rc_health": rc_health}
        )

        print(RF.formatted_log("Pre-flight: FAIL (health)", "ERROR"))
        return 1

    incidents.log(
        "INFO",
        "Pre-flight OK: health check passed",
        {"rc_health": rc_health, "rc_status": rc_status}
    )
    print(RF.formatted_log("Pre-flight: OK", "SUCCESS"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

