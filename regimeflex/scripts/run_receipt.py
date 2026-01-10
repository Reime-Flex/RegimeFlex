#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.exec_alpaca import dry_run_details


def load_latest_replay(root: Path) -> Optional[Dict[str, Any]]:
    # Check both possible locations for replays
    replays = root / "replays"
    if not replays.exists():
        # Try parent directory if we're in regimeflex
        parent_replays = root.parent / "replays"
        if parent_replays.exists():
            replays = parent_replays
        else:
            return None
    
    files = sorted(replays.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    p = files[0]
    obj = json.loads(p.read_text(encoding="utf-8"))
    obj["_path"] = str(p)
    return obj


def build_receipt(root: Path = Path(".")) -> Dict[str, Any]:
    replay = load_latest_replay(root)
    exec_mode = dry_run_details(root)

    receipt: Dict[str, Any] = {
        "execution_mode": exec_mode,
        "latest_replay": None,
        "as_of": None,
        "no_op": None,
        "no_op_reason": None,
    }

    if replay:
        receipt["latest_replay"] = replay.get("_path")
        receipt["as_of"] = replay.get("as_of")
        guards = (replay.get("guards") or {})
        receipt["no_op"] = bool(guards.get("no_op", False))
        receipt["no_op_reason"] = guards.get("no_op_reason", "")

    return receipt


if __name__ == "__main__":
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        root = cwd / "regimeflex"
    else:
        root = cwd
    
    print(json.dumps(build_receipt(root), indent=2))

