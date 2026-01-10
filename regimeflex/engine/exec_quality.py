# engine/exec_quality.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

def slippage_bps(side: str, fill_price: float, ref_price: float) -> float | None:
    """Positive is worse than ref."""
    if fill_price <= 0 or ref_price <= 0:
        return None
    mult = 1.0 if (side or "").upper() == "BUY" else -1.0
    return 1e4 * mult * (fill_price / ref_price - 1.0)

def rolling_stats(fills: List[Dict[str, Any]], window: int) -> Dict[str, Any]:
    vals = [x.get("slip_bps") for x in fills if isinstance(x.get("slip_bps"), (int,float))]
    vals = vals[-window:]
    if not vals:
        return {"count": 0, "avg_bps": None, "p95_bps": None}
    vs = sorted(vals)
    n = len(vs)
    p95 = vs[int(max(0, min(n-1, round(0.95*(n-1)))))]
    return {"count": n, "avg_bps": sum(vs)/n, "p95_bps": p95}

