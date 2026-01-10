# engine/bar_hygiene.py
from __future__ import annotations
from typing import Dict, Any, Tuple

def _last_row(df):
    return df.iloc[-1] if len(df) else None

def _prev_close(df):
    return float(df["close"].iloc[-2]) if len(df) >= 2 else None

def validate_last_bar(symbol: str, df, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Returns (ok, note). Does NOT mutate df.
    Expects columns: open, high, low, close, volume
    """
    if df is None or len(df) == 0:
        return False, "empty_df"
    r = _last_row(df)
    try:
        o = float(r["open"]); h = float(r["high"]); l = float(r["low"]); c = float(r["close"])
        v = float(r["volume"])
    except Exception:
        return False, "missing_fields"

    checks = cfg.get("checks", {}) or {}
    # positive prices
    if checks.get("positive_prices", True):
        if not (o > 0 and h > 0 and l > 0 and c > 0):
            return False, "non_positive_price"

    # monotonic OHLC
    if checks.get("ohlc_monotonic", True):
        lo_ref = min(o, c)
        hi_ref = max(o, c)
        if not (l <= lo_ref + 1e-12 and h + 1e-12 >= hi_ref and l <= h):
            return False, "ohlc_monotonic_fail"

    # non-negative volume
    if checks.get("non_negative_volume", True):
        if v < 0:
            return False, "negative_volume"

    # max gap vs prev close
    mgp = checks.get("max_gap_pct", None)
    if mgp is not None:
        pc = _prev_close(df)
        if pc and pc > 0:
            gap = abs(c - pc) / pc
            if gap > float(mgp):
                return False, f"gap_gt_{mgp:.2f}"

    return True, "OK"

