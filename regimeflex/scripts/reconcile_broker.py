#!/usr/bin/env python
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.exec_alpaca import get_broker_positions


def load_latest_replay(replays_dir: Path) -> Dict[str, Any]:
    """Load the most recent replay pack by modification time."""
    files = sorted(replays_dir.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No replay_*.json found in replays/")
    path = files[0]
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["_path"] = str(path)
    return obj


def main(argv) -> int:
    root = Path(".")
    replays_dir = root / "replays"

    if not replays_dir.exists():
        print(RF.formatted_log("replays/ directory not found.", "ERROR"))
        return 1

    try:
        pack = load_latest_replay(replays_dir)
    except FileNotFoundError as e:
        print(RF.formatted_log(str(e), "ERROR"))
        return 1

    as_of = pack.get("as_of", "")
    state = pack.get("state", {}) or {}
    internal = state.get("positions_after", {}) or {}

    print(RF.formatted_log(f"Using latest replay pack: {Path(pack.get('_path','')).name}", "INFO"))
    print(RF.formatted_log(f"As-of date (model view): {as_of}", "INFO"))
    print(RF.formatted_log(f"Internal positions_after: {internal}", "INFO"))

    # Fetch broker positions
    try:
        broker = get_broker_positions()
    except Exception as e:
        print(RF.formatted_log(f"Failed to fetch broker positions: {e}", "ERROR"))
        return 1

    print(RF.formatted_log(f"Broker positions: {broker}", "INFO"))

    # Normalise keys and floats to ints where appropriate
    def norm(pos: Dict[str, Any]) -> Dict[str, int]:
        """Normalize position dict: uppercase symbols, round to int."""
        out: Dict[str, int] = {}
        for k, v in (pos or {}).items():
            try:
                out[str(k).upper()] = int(round(float(v)))
            except Exception:
                out[str(k).upper()] = 0
        return out

    internal_n = norm(internal)
    broker_n = norm(broker)

    # Build union of symbols
    symbols = sorted(set(internal_n.keys()) | set(broker_n.keys()))

    mismatches = []
    print(RF.formatted_log("Recon summary (symbol, internal, broker, diff):", "INFO"))

    for sym in symbols:
        i_q = internal_n.get(sym, 0)
        b_q = broker_n.get(sym, 0)
        diff = b_q - i_q
        line = f"  {sym}: internal={i_q}, broker={b_q}, diff={diff}"
        if diff != 0:
            mismatches.append(line)
        print(line)

    if not mismatches:
        print(RF.formatted_log("Broker reconciliation OK (positions match).", "SUCCESS"))
        return 0

    print(RF.formatted_log("Broker reconciliation MISMATCH:", "RISK"))
    for m in mismatches:
        print(m)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

