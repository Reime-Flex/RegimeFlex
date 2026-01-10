# engine/sanity.py
from __future__ import annotations
from typing import Dict, Tuple

def check_mutual_exclusive(
    alloc: Dict[str, float],
    long_sym: str,
    short_sym: str,
    threshold: float = 0.05,
) -> Tuple[bool, str]:
    """Return (ok, note). ok=False if both sides exceed threshold."""
    wl = float(alloc.get(long_sym, 0.0))
    ws = float(alloc.get(short_sym, 0.0))
    both = (wl > threshold) and (ws > threshold)
    if both:
        return False, f"both_sides_active wl={wl:.2f} ws={ws:.2f} thr={threshold:.2f}"
    return True, "OK"

def clamp_smaller_side(
    alloc: Dict[str, float],
    long_sym: str,
    short_sym: str,
) -> Dict[str, float]:
    """Zero the smaller of the two sides in-place (returns the same dict)."""
    wl = float(alloc.get(long_sym, 0.0))
    ws = float(alloc.get(short_sym, 0.0))
    if wl >= ws:
        alloc[short_sym] = 0.0
    else:
        alloc[long_sym] = 0.0
    return alloc

