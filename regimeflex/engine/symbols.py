# engine/symbols.py
from __future__ import annotations
from typing import Tuple
from .config import Config
from .identity import RegimeFlexIdentity as RF
from .data import load_from_cache

def resolve_signal_underlier() -> Tuple[str, object]:
    """
    Returns (symbol_name, df) for the signal underlier.
    - If config asks for NDX but it's not in cache, falls back to QQQ and logs.
    - We only read from cache here; live fetching remains your fetch script's job.
    """
    cfg = Config(".")._load_yaml("config/exposure.yaml")
    sig = (cfg.get("signal") or {})
    underlier = str(sig.get("underlier", "QQQ")).upper()
    ndx_symbol = sig.get("ndx_symbol", "^NDX")
    fallback = sig.get("proxy_fallback", "QQQ")

    if underlier == "NDX":
        df = load_from_cache(ndx_symbol)
        if df is not None and not df.empty:
            RF.print_log(f"Signal underlier resolved: NDX ({ndx_symbol})", "INFO")
            return ndx_symbol, df
        RF.print_log(f"NDX cache missing ({ndx_symbol}) → falling back to {fallback}", "RISK")
        fb = load_from_cache(fallback)
        if fb is None or fb.empty:
            raise RuntimeError(f"Fallback cache missing: {fallback}")
        return fallback, fb

    # default: QQQ
    df = load_from_cache("QQQ")
    if df is None or df.empty:
        raise RuntimeError("QQQ cache missing")
    RF.print_log("Signal underlier resolved: QQQ", "INFO")
    return "QQQ", df
