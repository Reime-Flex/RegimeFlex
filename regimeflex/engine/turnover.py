# engine/turnover.py
from __future__ import annotations
from typing import Dict, Tuple
import pandas as pd
from .identity import RegimeFlexIdentity as RF

def _mv_from_weights(weights: Dict[str, float], equity: float) -> Dict[str, float]:
    return {k: float(v) * float(equity) for k, v in weights.items()}

def _weights_from_mv(mv: Dict[str, float], equity: float) -> Dict[str, float]:
    if equity <= 0: 
        return {k: 0.0 for k in mv}
    return {k: float(v) / float(equity) for k, v in mv.items()}

def _compute_turnover_dollars(current_mv: Dict[str, float], desired_mv: Dict[str, float]) -> float:
    # sum of absolute dollar changes across sides
    sides = set(current_mv.keys()) | set(desired_mv.keys())
    return sum(abs(float(desired_mv.get(s,0.0)) - float(current_mv.get(s,0.0))) for s in sides)

def enforce_turnover_cap(
    alloc_weights: Dict[str, float],           # desired weights (e.g., {"QQQ": 0.80, "PSQ": 0.00})
    positions_before: Dict[str, float],        # shares before for each side symbol
    last_prices: Dict[str, float],             # price per symbol (same symbols used in weights)
    equity: float,                             
    max_turnover_frac: float,                  # 0.15 = 15%
    mode: str = "clamp",                       # "clamp" or "skip"
) -> Tuple[Dict[str, float], Dict[str, float], float, str]:
    """
    Returns (new_weights, desired_mv, turnover_frac, note)
      - new_weights: possibly scaled weights after turnover cap
      - desired_mv: dollars per side from new_weights
      - turnover_frac: turnover / equity
      - note: "OK" or explanation like "turnover 0.23>0.15 -> clamp×0.652"
    """
    # current market value per side (shares * price)
    current_mv = {}
    for sym, sh in positions_before.items():
        if sym in last_prices:
            price = float(last_prices[sym])
            # Handle NaN prices by treating as 0.0
            if pd.isna(price):
                current_mv[sym] = 0.0
            else:
                current_mv[sym] = float(sh) * price
    # ensure both sides exist
    for sym in alloc_weights.keys():
        current_mv.setdefault(sym, 0.0)

    desired_mv = _mv_from_weights(alloc_weights, equity)
    turnover = _compute_turnover_dollars(current_mv, desired_mv)
    turnover_frac = float(turnover) / float(equity) if equity > 0 else 0.0

    if max_turnover_frac <= 0:
        return alloc_weights, desired_mv, turnover_frac, "cap=0 → no limit"

    if turnover_frac <= max_turnover_frac:
        return alloc_weights, desired_mv, turnover_frac, "OK"

    # over the cap:
    if mode.lower() == "skip":
        RF.print_log(f"Turnover cap hit: {turnover_frac:.3f}>{max_turnover_frac:.3f} → SKIP", "RISK")
        # return weights equivalent to holding current_mv (no change)
        new_w = _weights_from_mv(current_mv, equity)
        new_desired_mv = current_mv
        note = f"turnover {turnover_frac:.3f}>{max_turnover_frac:.3f} -> skip"
        return new_w, new_desired_mv, turnover_frac, note

    # clamp: scale change vector toward current by factor s = cap / turnover
    s = max_turnover_frac / turnover_frac if turnover_frac > 0 else 1.0
    clamped_mv = {k: current_mv.get(k,0.0) + s * (desired_mv.get(k,0.0) - current_mv.get(k,0.0))
                  for k in set(current_mv.keys()) | set(desired_mv.keys())}
    new_w = _weights_from_mv(clamped_mv, equity)
    note = f"turnover {turnover_frac:.3f}>{max_turnover_frac:.3f} -> clamp×{s:.3f}"
    RF.print_log(f"Turnover cap applied: {note}", "RISK")
    return new_w, clamped_mv, turnover_frac, note
