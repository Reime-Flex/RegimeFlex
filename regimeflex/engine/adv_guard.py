# engine/adv_guard.py
from __future__ import annotations
from typing import List, Dict, Any
import math

def enforce_adv_cap(
    intents: List[Dict[str, Any]],
    adv_map: Dict[str, float],
    crit_frac: float,
    action: str = "block",
) -> Dict[str, Any]:
    """
    intents: [{'symbol','qty','price',...}]
    adv_map: {'QQQ': ADV$, 'PSQ': ADV$, ...}
    Returns:
      {
        "violations": [ {symbol, qty, price, notional, adv, of_adv, max_qty}... ],
        "blocked": bool,
        "scaled_intents": [...],   # present only if action == "scale"
      }
    """
    violations = []
    for it in intents or []:
        sym = str(it.get("symbol","")).upper()
        qty = float(it.get("qty",0))
        px  = float(it.get("price",0))
        notional = abs(qty * px)
        adv = float(adv_map.get(sym, 0.0))
        of_adv = (notional / adv) if adv > 0 else float("inf")
        if of_adv > crit_frac:
            max_notional = crit_frac * adv if adv > 0 else 0.0
            max_qty = 0.0 if px <= 0 else math.floor(max_notional / px)
            violations.append({
                "symbol": sym, "qty": qty, "price": px,
                "notional": notional, "adv": adv, "of_adv": of_adv,
                "max_qty": max_qty
            })

    if not violations:
        return {"violations": [], "blocked": False}

    if action.lower() == "scale":
        # Scale down only violating intents; others unchanged
        new_intents = []
        vmap = {v["symbol"]: v for v in violations}
        for it in intents:
            sym = str(it.get("symbol","")).upper()
            v = vmap.get(sym)
            if v:
                # preserve side sign
                side = (it.get("side","BUY") or "BUY").upper()
                max_qty = v["max_qty"]
                if max_qty <= 0:
                    # drop this intent
                    continue
                new_q = max_qty if side == "BUY" else -max_qty
                new_it = {**it, "qty": new_q}
                new_intents.append(new_it)
            else:
                new_intents.append(it)
        return {"violations": violations, "blocked": False, "scaled_intents": new_intents}

    # default: block
    return {"violations": violations, "blocked": True}

