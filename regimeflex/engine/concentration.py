# engine/concentration.py
from __future__ import annotations
from typing import Dict, Tuple

def side_concentration(weights: Dict[str, float]) -> float:
    """
    Return absolute net exposure fraction: abs(sum_longs - sum_shorts).
    Expects weights in fractional terms (e.g., 0.25, -0.10).
    """
    total = 0.0
    for _, w in (weights or {}).items():
        total += float(w)
    return abs(total)

def symbol_peak(weights: Dict[str, float]) -> Tuple[str, float]:
    """
    Return (symbol, abs_weight) for the most concentrated single name.
    """
    if not weights:
        return "", 0.0
    sym = max(weights, key=lambda k: abs(float(weights[k])))
    return sym, abs(float(weights[sym]))

def badge(value: float, warn: float, crit: float) -> str:
    if value >= crit:  return "RED"
    if value >= warn:  return "AMBER"
    return "GREEN"

