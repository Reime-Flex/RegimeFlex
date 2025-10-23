# engine/reconcile_positions.py
from __future__ import annotations
from pathlib import Path
import json
from typing import Dict, Tuple, List
from datetime import datetime, timezone

from .identity import RegimeFlexIdentity as RF
from .config import Config
from .symnorm import map_keys_upper, sym_upper

FILLS_FILE = Path("logs/trading/fills_state.jsonl")

def _read_fills() -> List[dict]:
    if not FILLS_FILE.exists():
        return []
    out = []
    with FILLS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

def effective_positions_before(
    raw_positions_before: Dict[str, float],
    broker_positions_snapshot: Dict[str, float] | None = None,
) -> Tuple[Dict[str, float], str]:
    """
    Returns (positions_effective, note)
    Priority:
      1) If broker_positions_snapshot provided (e.g., from Alpaca positions API), use it.
      2) Else start from raw_positions_before and apply latest known filled_qty deltas from fills_state.
    Only adjusts symbols present in raw_positions_before OR mentioned in fills log.
    """
    # 1) Trust broker snapshot if available
    if broker_positions_snapshot:
        RF.print_log("Positions source: broker snapshot", "INFO")
        return map_keys_upper(broker_positions_snapshot), "broker_snapshot"

    # 2) Apply last known filled_qty to local view
    eff = map_keys_upper(raw_positions_before)
    fills = _read_fills()
    # Sort by ts to apply in-order
    def _parse_ts(s: str) -> datetime:
        try:
            return datetime.fromisoformat(s.replace("Z","+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    fills.sort(key=lambda r: _parse_ts(r.get("ts","")))
    applied = 0

    for r in fills:
        sym = sym_upper(str(r.get("symbol","")))
        side = str(r.get("side","")).lower()
        status = str(r.get("status","")).lower()
        fq = r.get("filled_qty")
        q = r.get("qty", 0.0)

        # Only adjust on known/filled statuses
        filled_shares = None
        if fq is not None:
            try:
                filled_shares = float(fq)
            except Exception:
                filled_shares = None

        # If we don't know the filled quantity, skip (we won't assume full fill)
        if filled_shares is None:
            continue

        # Update position: buy adds, sell subtracts
        delta = filled_shares if side == "buy" else -filled_shares
        prev = float(eff.get(sym, 0.0))
        eff[sym] = prev + delta
        applied += 1

    if applied > 0:
        RF.print_log(f"Applied {applied} fill adjustments from local state.", "INFO")
        return eff, "local_fills_applied"

    RF.print_log("Positions source: raw (no fills applied)", "INFO")
    return eff, "raw"
