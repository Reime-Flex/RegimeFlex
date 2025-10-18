from __future__ import annotations
from typing import List, Dict, Any
from .exec_planner import OrderIntent

def compare_intents_vs_orders(intents: List[OrderIntent], orders: List[dict]) -> dict:
    """
    Compare planned intents with Alpaca responses (or dry-run payloads).
    Returns a dict with 'matches' and 'mismatches' lists.
    Matching heuristic: (symbol, side, qty rounded 1e-6, tif)
    """
    def key_from_intent(it: OrderIntent):
        return (it.symbol, it.side.lower(), round(float(it.qty), 6), it.time_in_force.lower())

    def key_from_order(o: dict):
        sym = o.get("symbol")
        side = (o.get("side") or o.get("request", {}).get("side", "")).lower()
        # Alpaca may return qty as str; dry-run payloads keep float
        raw_qty = o.get("qty", o.get("request", {}).get("qty", 0))
        try:
            qty = round(float(raw_qty), 6)
        except Exception:
            qty = 0.0
        tif = (o.get("time_in_force") or o.get("request", {}).get("time_in_force", "")).lower()
        return (sym, side, qty, tif)

    intent_map = {key_from_intent(it): it for it in intents}
    matches, mismatches = [], []

    for o in orders:
        k = key_from_order(o)
        if k in intent_map:
            matches.append({"intent": intent_map[k], "order": o})
        else:
            mismatches.append({"order": o})

    # Any intents with no matched order?
    unmatched_intents = [it for k,it in intent_map.items() if all(key_from_order(o) != k for o in orders)]

    return {
        "matches": matches,
        "mismatches": mismatches,
        "unmatched_intents": unmatched_intents
    }
