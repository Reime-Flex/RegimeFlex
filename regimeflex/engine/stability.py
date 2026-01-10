# engine/stability.py
from __future__ import annotations
from typing import Iterable, Dict, Tuple, List

def _dir(series: Iterable[str]) -> List[str]:
    # normalize directions to one of: "LONG", "SHORT", "FLAT"
    out = []
    for s in series:
        v = (s or "").upper()
        if v not in ("LONG","SHORT","FLAT"):
            v = "FLAT"
        out.append(v)
    return out

def flip_count(directions: Iterable[str]) -> int:
    ds = _dir(directions)
    flips = 0
    prev = None
    for d in ds:
        if prev is not None and d != prev:
            flips += 1
        prev = d
    return flips

def stability_score(directions: Iterable[str], denom: int) -> float:
    if denom <= 0:
        return 0.0
    return max(0.0, 1.0 - (flip_count(directions) / float(denom)))

