# engine/exposure_delta.py
from __future__ import annotations
from typing import Dict

def current_exposure_weights(positions: Dict[str, float], prices: Dict[str, float], equity_ref: float) -> Dict[str, float]:
    """
    Returns weights (fraction of equity) for TQQQ and SQQQ based on positions_before.
    If a symbol is absent, treat as 0.
    """
    if equity_ref <= 0:
        return {"TQQQ": 0.0, "SQQQ": 0.0}
    t_mv = float(positions.get("TQQQ", 0.0)) * float(prices.get("TQQQ", 0.0))
    s_mv = float(positions.get("SQQQ", 0.0)) * float(prices.get("SQQQ", 0.0))
    return {
        "TQQQ": t_mv / equity_ref,
        "SQQQ": s_mv / equity_ref,
    }

def exposure_delta(prev_w: Dict[str, float], desired_w: Dict[str, float]) -> Dict[str, float]:
    """
    Δ = desired - prev (per-side).
    """
    return {
        "TQQQ": float(desired_w.get("TQQQ", 0.0) - prev_w.get("TQQQ", 0.0)),
        "SQQQ": float(desired_w.get("SQQQ", 0.0) - prev_w.get("SQQQ", 0.0)),
    }
