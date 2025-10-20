# engine/instruments.py
from __future__ import annotations
from typing import Tuple, Dict
from .config import Config
from .identity import RegimeFlexIdentity as RF

def resolve_execution_pair() -> Dict[str, str]:
    ex = Config(".")._load_yaml("config/execution.yaml")
    pair = (ex.get("pair") or "QQQ_PSQ").upper()
    mp = (ex.get("mapping") or {}).get(pair, {})
    long_symbol  = mp.get("long_symbol", "QQQ")
    short_symbol = mp.get("short_symbol", "PSQ")
    long_ref     = mp.get("long_price_ref", long_symbol)
    short_ref    = mp.get("short_price_ref", short_symbol)
    RF.print_log(f"Execution pair: {pair} → long={long_symbol} short={short_symbol}", "INFO")
    return {
        "pair": pair,
        "long": long_symbol,
        "short": short_symbol,
        "long_ref": long_ref,
        "short_ref": short_ref,
    }
