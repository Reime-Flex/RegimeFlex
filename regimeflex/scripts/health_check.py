#!/usr/bin/env python
from __future__ import annotations

import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF


def esc(x: str) -> str:
    return (
        str(x)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def load_latest_replay() -> Dict[str, Any]:
    """Load the most recent replay pack by modification time."""
    replays_dir = Path("replays")
    if not replays_dir.exists():
        raise FileNotFoundError("replays/ directory not found")
    files = sorted(replays_dir.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No replay files in replays/")
    path = files[0]
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["_path"] = str(path)
    return obj


def run_cmd(label: str, cmd: list[str]) -> bool:
    """Run a command and return True if exit code is 0, False otherwise."""
    print(RF.formatted_log(f"Running {label}: {' '.join(cmd)}", "INFO"))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            print(RF.formatted_log(f"{label}: PASS", "SUCCESS"))
            if p.stdout:
                # Print stdout for visibility
                for line in p.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"  {line}")
            return True
        else:
            print(RF.formatted_log(f"{label}: FAIL (exit {p.returncode})", "ERROR"))
            if p.stderr:
                for line in p.stderr.strip().split('\n'):
                    if line.strip():
                        print(f"  {line}", file=sys.stderr)
            return False
    except Exception as e:
        print(RF.formatted_log(f"{label}: FAIL (exception: {e})", "ERROR"))
        return False


def main():
    print(RF.formatted_log("Starting unified RegimeFlex health check", "INFO"))

    ##############################################
    # 1. Load latest replay pack
    ##############################################
    try:
        replay = load_latest_replay()
    except Exception as e:
        print(RF.formatted_log(f"Cannot load latest replay: {e}", "ERROR"))
        return 1

    rp_path = replay.get("_path", "")
    as_of = replay.get("as_of", "")
    prov = replay.get("provenance", {}) or {}
    model = prov.get("model", {}) or {}

    # Extract just the filename for display
    rp_display = Path(rp_path).name if rp_path else "unknown"

    print(RF.formatted_log(f"Latest replay: {rp_display}", "INFO"))
    print(RF.formatted_log(f"As-of date: {as_of}", "INFO"))
    print(RF.formatted_log(f"Model: {model.get('name', 'RegimeFlex')} v{model.get('version', '0.0.0')}", "INFO"))

    ##############################################
    # 2. Replay consistency check
    ##############################################
    ok_replay = run_cmd("replay-latest", ["make", "replay-latest"])

    ##############################################
    # 3. Broker reconciliation
    ##############################################
    ok_broker = run_cmd("reconcile-broker", ["make", "reconcile-broker"])

    ##############################################
    # 4. Config drift check
    ##############################################
    # Compare config_hash directly to hash inside replay
    expected_hash = prov.get("config_hash16") or replay.get("brand", {}).get("config_hash16")
    print(RF.formatted_log(f"Config hash16 in replay: {expected_hash}", "INFO"))

    # Recompute config hash using the existing hash utility
    from engine.config_hash import config_snapshot_hash
    current_hash = config_snapshot_hash(Path("."))[1]  # [1] is the short16 hash
    print(RF.formatted_log(f"Current config hash16: {current_hash}", "INFO"))

    ok_hash = (expected_hash == current_hash)
    if ok_hash:
        print(RF.formatted_log("Config drift check: PASS", "SUCCESS"))
    else:
        print(RF.formatted_log("Config drift check: FAIL (config hashes do NOT match)", "ERROR"))

    ##############################################
    # 5. Summarize
    ##############################################
    all_ok = ok_replay and ok_broker and ok_hash

    print("------------------------------------------------------------")
    if all_ok:
        print(RF.formatted_log("RegimeFlex Health Check: ALL GREEN", "SUCCESS"))
        return 0
    else:
        print(RF.formatted_log("RegimeFlex Health Check: FAIL", "ERROR"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
