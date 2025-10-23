# engine/symnorm.py
from __future__ import annotations
from typing import Dict, Iterable

def sym_upper(s: str) -> str:
    return (s or "").upper()

def map_keys_upper(d: Dict) -> Dict:
    return { sym_upper(k): v for k, v in (d or {}).items() }

def ensure_keys_upper(d: Dict, keys: Iterable[str]) -> Dict:
    u = map_keys_upper(d)
    for k in keys:
        if k.upper() not in u:
            u[k.upper()] = u.get(k, 0.0)  # keep missing as 0/None
    return u
