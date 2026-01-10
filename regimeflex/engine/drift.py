# engine/drift.py
from __future__ import annotations
from typing import Dict, List, Tuple

def compute_position_drift(
    local_pos: Dict[str, float],     # reconciled: positions_before (effective), UPPERCASE
    broker_pos: Dict[str, float] | None,  # snapshot from broker (if available), UPPERCASE
    prices: Dict[str, float],        # UPPERCASE, latest common-date prices
    symbols: List[str],              # which symbols to check (e.g., ["QQQ","PSQ"])
    shares_eps: float = 1.0,
    notional_eps: float = 200.0,
) -> Tuple[bool, Dict[str, dict], str]:
    """
    Returns (warn, per_sym, note)
      - warn: True if any symbol exceeds thresholds
      - per_sym: {SYM: {"local_sh":..,"broker_sh":..,"d_sh":..,"d_notional":..}}
      - note: "no_broker_snapshot" | "OK" | "WARN"
    """
    if not broker_pos:
        return False, {}, "no_broker_snapshot"

    warn = False
    out: Dict[str, dict] = {}
    for s in symbols:
        ls = float(local_pos.get(s, 0.0))
        bs = float(broker_pos.get(s, 0.0))
        d_sh = bs - ls
        px  = float(prices.get(s, 0.0))
        d_not = abs(d_sh) * (px if px == px else 0.0)
        hit = (abs(d_sh) > shares_eps) or (d_not > notional_eps)
        warn = warn or hit
        out[s] = {
            "local_sh": round(ls, 6),
            "broker_sh": round(bs, 6),
            "d_sh": round(d_sh, 6),
            "d_notional": round(d_not, 2),
            "hit": hit,
        }
    return warn, out, ("WARN" if warn else "OK")

