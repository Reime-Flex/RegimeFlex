# engine/exposure_delta.py
from __future__ import annotations
from typing import Dict, Iterable

def current_exposure_weights(
    positions: Dict[str, float],
    prices: Dict[str, float],
    equity_ref: float,
    sides: Iterable[str],
) -> Dict[str, float]:
    """
    Returns weights (fraction of equity) for the provided side symbols.
    Example sides: ["QQQ","PSQ"] or ["TQQQ","SQQQ"] depending on execution pair.
    """
    out: Dict[str, float] = {}
    if equity_ref <= 0:
        for s in sides: out[s] = 0.0
        return out
    for s in sides:
        sh = float(positions.get(s, 0.0))
        px = float(prices.get(s, 0.0))
        mv = sh * px
        out[s] = mv / float(equity_ref)
    return out

def exposure_delta(prev_w: Dict[str, float], desired_w: Dict[str, float], sides: Iterable[str]) -> Dict[str, float]:
    """Δ = desired - prev, for the provided sides."""
    out: Dict[str, float] = {}
    for s in sides:
        out[s] = float(desired_w.get(s, 0.0) - prev_w.get(s, 0.0))
    return out
