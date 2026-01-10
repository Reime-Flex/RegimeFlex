#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path
import subprocess

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF

def main(argv: list[str]) -> int:
    root = Path(".")
    replays_dir = root / "replays"

    if not replays_dir.exists():
        print(RF.formatted_log(f"Replays directory not found: {replays_dir}", "ERROR"))
        return 1

    # Find all replay_*.json files
    files = sorted(replays_dir.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(RF.formatted_log("No replay_*.json files found in replays/.", "ERROR"))
        return 1

    latest = files[0]
    print(RF.formatted_log(f"Latest replay pack: {latest.name}", "INFO"))

    # Call the existing replay_from_pack.py script
    cmd = [sys.executable, "scripts/replay_from_pack.py", str(latest)]
    result = subprocess.run(cmd)

    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

