# engine/harmonize.py
from __future__ import annotations
from typing import Dict, Tuple

def round_shares(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    return round(round(qty / step) * step, 9)

def harmonize_exposure(
    prev_w: Dict[str, float],          # previous weights per symbol
    desired_w: Dict[str, float],       # desired weights per symbol
    prices: Dict[str, float],          # price per symbol
    equity: float,
    share_step: float = 0.001,
    exposure_eps: float = 0.00005,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Returns (new_weights, new_shares) after snapping to share_step and snapping
    desired to prev when within exposure_eps.
    """
    out_w: Dict[str, float] = {}
    out_sh: Dict[str, float] = {}
    for s, w in desired_w.items():
        p = float(prices.get(s, 0.0))
        if equity <= 0 or p <= 0:
            out_w[s] = 0.0
            out_sh[s] = 0.0
            continue
        # epsilon snap
        w_prev = float(prev_w.get(s, 0.0))
        w_eff = w_prev if abs(w - w_prev) < exposure_eps else w
        # convert to shares and round to grid
        sh = (w_eff * equity) / p
        sh_r = round_shares(sh, share_step)
        # back to weight after rounding
        w_r = (sh_r * p) / equity
        out_w[s] = float(w_r)
        out_sh[s] = float(sh_r)
    return out_w, out_sh

