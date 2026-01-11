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
from engine.window_gate import window_gate_check
from engine.market_day_gate import market_day_check


def run(cmd: list[str], label: str) -> int:
    print(RF.formatted_log(f"Running {label}: {' '.join(cmd)}", "INFO"))
    p = subprocess.run(cmd)
    return int(p.returncode)


def main() -> int:
    # Use absolute path from paths module
    from regimeflex.config.paths import PROJECT_ROOT
    root = PROJECT_ROOT
    
    # For make commands, use project root
    make_cwd = PROJECT_ROOT
    script_path = PROJECT_ROOT / "regimeflex" / "scripts" / "run_offline_from_config.py"
    
    incidents = IncidentLogger(root=root)

    # Check window gate before proceeding
    cfg = Config(root)
    schedule_cfg = cfg._load_yaml("config/schedule.yaml") if (cfg.root / "config/schedule.yaml").exists() else {}
    gate = window_gate_check(schedule_cfg)

    if not gate.get("allowed", False):
        incidents.log("CRITICAL", "Gated live run blocked by window gate", gate)
        reason = gate.get("reason", "Window gate check failed")
        print(RF.formatted_log(f"Gated live run: BLOCKED ({reason})", "ERROR"))
        return 1

    # Check market day gate
    md_cfg = (schedule_cfg.get("market_day_gate") or {})
    if md_cfg.get("enabled", False):
        md = market_day_check(md_cfg)
        if not md.get("allowed", False):
            incidents.log("CRITICAL", "Gated live run blocked by market day gate", md)
            reason = md.get("reason", "Market day gate check failed")
            print(RF.formatted_log(f"Gated live run: BLOCKED ({reason})", "ERROR"))
            return 1

    # Run preflight check
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(str(make_cwd))
        rc_pre = run(["make", "preflight"], "preflight")
    finally:
        os.chdir(original_cwd)
    
    if rc_pre != 0:
        print(RF.formatted_log("Gated live run: BLOCKED (preflight failed)", "ERROR"))
        incidents.log("CRITICAL", "Gated live run blocked: preflight failed", {"rc_preflight": rc_pre})
        return 1

    # If preflight is OK, run the live runner entrypoint
    # Use the actual live runner script (run_offline_from_config.py)
    rc_live = run([sys.executable, str(script_path)], "run_live")
    if rc_live != 0:
        incidents.log("ERROR", "Live run failed", {"rc_live": rc_live})
        print(RF.formatted_log("Gated live run: LIVE FAILED", "ERROR"))
        return 1

    incidents.log("INFO", "Gated live run completed successfully", {"rc_live": rc_live})
    print(RF.formatted_log("Gated live run: OK", "SUCCESS"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

