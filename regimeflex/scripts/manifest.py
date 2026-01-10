#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.model_manifest import load_model_manifest
from engine.exec_alpaca import dry_run_details
from engine.config_hash import config_snapshot_hash


def load_latest_replay(replays_dir: Path) -> Dict[str, Any] | None:
    files = sorted(replays_dir.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    path = files[0]
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["_path"] = str(path)
    return obj


def main() -> int:
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        # We're at project root, use regimeflex as root
        root = cwd / "regimeflex"
    else:
        # We're in regimeflex directory
        root = cwd
    
    cfg = Config(root)

    # Model manifest
    mm = load_model_manifest(root)
    model = (mm.get("model") or {})
    model_name = model.get("name", "RegimeFlex")
    model_ver = model.get("version", "0.0.0")

    # Config hash
    _, hash16, _ = config_snapshot_hash(root)

    # Execution mode (source-aware)
    exec_mode = dry_run_details(root)

    # Risk config: pull only the blocks we know exist (no guessing)
    risk_cfg = cfg._load_yaml("config/risk.yaml") if (cfg.root / "config/risk.yaml").exists() else {}
    kill_cfg = (risk_cfg.get("kill_switch") or {})
    anomaly_cfg = (risk_cfg.get("anomaly_alerts") or {})

    # Latest replay context (if present)
    # Check both possible locations for replays
    replays_dir = root / "replays"
    if not replays_dir.exists() and (cwd / "replays").exists():
        replays_dir = cwd / "replays"
    replay = load_latest_replay(replays_dir)
    replay_path_full = replay.get("_path") if replay else None
    replay_path = Path(replay_path_full).name if replay_path_full else None
    as_of = replay.get("as_of") if replay else None
    guards = (replay.get("guards") or {}) if replay else {}
    no_op = bool(guards.get("no_op", False)) if replay else None
    no_op_reason = guards.get("no_op_reason", "") if replay else ""

    print(RF.formatted_log("Manifest (read-only snapshot)", "INFO"))
    print("------------------------------------------------------------")
    print(f"Model: {model_name}  v{model_ver}")
    print(f"Config hash16: {hash16}")
    print("")
    print("Execution mode:")
    print(f"  dry_run: {exec_mode.get('dry_run', False)}")
    print(f"  source:  {exec_mode.get('source', 'none')}")
    print(f"  env_value: {exec_mode.get('env_value','')}")
    print(f"  config_value: {exec_mode.get('config_value', False)}")
    print("")
    print("Risk controls:")
    print(f"  kill_switch.enabled: {kill_cfg.get('enabled', False)}")
    print(f"  kill_switch.max_slippage_bps: {kill_cfg.get('max_slippage_bps', None)}")
    print(f"  kill_switch.max_red_liquidity_checks: {kill_cfg.get('max_red_liquidity_checks', None)}")
    print(f"  kill_switch.block_on_adv_violation: {kill_cfg.get('block_on_adv_violation', None)}")
    print("")
    print(f"  anomaly_alerts.enabled: {anomaly_cfg.get('enabled', False)}")
    print(f"  anomaly_alerts.slippage_soft_bps: {anomaly_cfg.get('slippage_soft_bps', None)}")
    print(f"  anomaly_alerts.liquidity_red_soft: {anomaly_cfg.get('liquidity_red_soft', None)}")
    print("")
    print("Latest replay:")
    if replay:
        print(f"  file: {replay_path}")
        print(f"  as_of: {as_of}")
        print(f"  no_op: {no_op}")
        print(f"  no_op_reason: {no_op_reason}")
    else:
        print("  none found in replays/")
    print("------------------------------------------------------------")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

