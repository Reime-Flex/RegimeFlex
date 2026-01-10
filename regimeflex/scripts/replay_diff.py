#!/usr/bin/env python
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF


def load_pack(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def intents_signature(intents: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
    """
    Reduce intents to a stable signature:
    (symbol, side, qty) sorted by (symbol, side, qty).
    """
    sig = []
    for it in intents or []:
        sym = str(it.get("symbol", "")).upper()
        side = str(it.get("side", "")).upper()
        # Handle both "qty" and "shares" fields for compatibility
        qty_val = it.get("qty") or it.get("shares") or 0.0
        try:
            qty = float(qty_val)
        except Exception:
            qty = 0.0
        sig.append((sym, side, qty))
    sig.sort()
    return sig


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/replay_diff.py old_replay.json new_replay.json")
        return 1

    p1 = Path(argv[1])
    p2 = Path(argv[2])

    if not p1.exists():
        print(RF.formatted_log(f"File not found: {p1}", "ERROR"))
        return 1
    if not p2.exists():
        print(RF.formatted_log(f"File not found: {p2}", "ERROR"))
        return 1

    try:
        a = load_pack(p1)
        b = load_pack(p2)
    except json.JSONDecodeError as e:
        print(RF.formatted_log(f"Invalid JSON in replay pack: {e}", "ERROR"))
        return 1
    except Exception as e:
        print(RF.formatted_log(f"Error reading replay pack: {e}", "ERROR"))
        return 1

    print(RF.formatted_log(f"Comparing replays:", "INFO"))
    print(RF.formatted_log(f"  OLD: {p1}", "INFO"))
    print(RF.formatted_log(f"  NEW: {p2}", "INFO"))

    mismatches = []

    # 1) As-of date
    if a.get("as_of") != b.get("as_of"):
        mismatches.append(f"as_of: {a.get('as_of')} != {b.get('as_of')}")

    # 2) Config hash16
    a_ch16 = (a.get("brand", {}) or {}).get("config_hash16") or (a.get("provenance", {}) or {}).get("config_hash16")
    b_ch16 = (b.get("brand", {}) or {}).get("config_hash16") or (b.get("provenance", {}) or {}).get("config_hash16")
    if a_ch16 != b_ch16:
        mismatches.append(f"config_hash16: {a_ch16} != {b_ch16}")

    # 3) Positions BEFORE
    a_state = a.get("state", {}) or {}
    b_state = b.get("state", {}) or {}

    if a_state.get("positions_before", {}) != b_state.get("positions_before", {}):
        mismatches.append(f"positions_before differ")

    # 4) Positions AFTER
    if a_state.get("positions_after", {}) != b_state.get("positions_after", {}):
        mismatches.append(f"positions_after differ")

    # 5) Intents signature
    a_sig = intents_signature(a_state.get("intents", []))
    b_sig = intents_signature(b_state.get("intents", []))
    if a_sig != b_sig:
        mismatches.append(f"intents signature differ:\n  OLD: {a_sig}\n  NEW: {b_sig}")

    # 6) Guards: no_op + reason
    a_g = a.get("guards", {}) or {}
    b_g = b.get("guards", {}) or {}

    if bool(a_g.get("no_op", False)) != bool(b_g.get("no_op", False)):
        mismatches.append(f"guards.no_op: {a_g.get('no_op')} != {b_g.get('no_op')}")

    if str(a_g.get("no_op_reason", "")) != str(b_g.get("no_op_reason", "")):
        mismatches.append(f"guards.no_op_reason: {a_g.get('no_op_reason')} != {b_g.get('no_op_reason')}")

    if not mismatches:
        print(RF.formatted_log("Replay packs MATCH at high-level decisions.", "SUCCESS"))
        return 0

    print(RF.formatted_log("Replay packs differ:", "RISK"))
    for m in mismatches:
        print(" -", m)

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

