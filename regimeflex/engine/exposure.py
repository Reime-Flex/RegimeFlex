# engine/exposure.py
from __future__ import annotations
import pandas as pd
import numpy as np
from .config import Config
from .identity import RegimeFlexIdentity as RF

def compute_sma(df: pd.DataFrame, n: int) -> pd.Series:
    return df["close"].rolling(n).mean()

def compute_bbands(df: pd.DataFrame, n: int, std: float) -> tuple[pd.Series, pd.Series]:
    ma = df["close"].rolling(n).mean()
    sigma = df["close"].rolling(n).std()
    upper = ma + std * sigma
    lower = ma - std * sigma
    return upper, lower

def ndx_extension(df: pd.DataFrame, slow_ma: int) -> float:
    sma_slow = compute_sma(df, slow_ma).iloc[-1]
    close = df["close"].iloc[-1]
    return (close / sma_slow - 1.0) if sma_slow > 0 else 0.0

def _realized_vol(series: pd.Series, n: int) -> float:
    # daily pct-change annualized stdev over n days
    r = series.pct_change().dropna().tail(n)
    if r.empty:
        return 0.0
    return float(r.std(ddof=0) * np.sqrt(252))

def exposure_allocator(df: pd.DataFrame) -> dict:
    """
    Returns desired exposure weights for TQQQ and SQQQ based on
    trend (fast vs slow), extension, Bollinger momentum (with confirmation),
    and a realized-volatility dampener.
    """
    cfg = Config(".")._load_yaml("config/exposure.yaml")
    fast, slow = cfg["trend"]["fast_ma"], cfg["trend"]["slow_ma"]
    ext_factor = cfg["weights"]["extension_factor"]
    bb_p, bb_std = cfg["weights"]["bb_period"], cfg["weights"]["bb_std"]
    max_exp, min_exp = cfg["weights"]["max_exposure_pct"], cfg["weights"]["min_exposure_pct"]

    # MAs and BBs
    sma_fast_series = compute_sma(df, fast)
    sma_fast = sma_fast_series.iloc[-1]
    sma_slow = compute_sma(df, slow).iloc[-1]
    close = df["close"].iloc[-1]
    upper, lower = compute_bbands(df, bb_p, bb_std)
    upper_now = upper.iloc[-1]

    # Basic states
    in_downtrend = sma_fast < sma_slow
    ext = ndx_extension(df, slow)

    # Momentum with confirmations
    conf = cfg.get("confirmation", {}) or {}
    momentum = close > upper_now
    if conf.get("momentum_requires_close_above_fast", True):
        momentum = momentum and (close > sma_fast)
    if conf.get("momentum_requires_slope_up", True):
        # slope up: fast MA today > fast MA yesterday
        if len(sma_fast_series) >= 2 and pd.notna(sma_fast_series.iloc[-2]):
            momentum = momentum and (sma_fast_series.iloc[-1] > sma_fast_series.iloc[-2])

    # Base weight, reduced by extension
    base = max(min(max_exp, cfg["weights"]["base_risk"]), 0.0)
    adj = np.exp(-ext_factor * abs(ext))
    weight = base * adj

    # Volatility dampener
    vd = cfg.get("vol_dampener", {}) or {}
    if vd.get("enabled", True):
        lookback = int(vd.get("lookback_days", 20))
        cap_rvol = float(vd.get("cap_rvol", 0.25))
        floor_scale = float(vd.get("floor_scale", 0.60))
        rvol = _realized_vol(df["close"], lookback)
        if rvol > cap_rvol:
            # linear scale-down from 1.0 at cap_rvol to floor_scale at 2×cap
            x = min(2.0, rvol / max(cap_rvol, 1e-9))
            scale = max(floor_scale, 2.0 - x)  # 1 at x=1, → floor at x=2
            weight *= scale
            RF.print_log(f"Vol dampener active: rVol{lookback}={rvol:.2%} scale={scale:.2f}", "RISK")

    # Momentum boost (after damping) but capped
    if (not in_downtrend) and momentum:
        weight = min(weight * 1.30, max_exp)

    # Clamp to bounds
    weight = float(np.clip(weight, min_exp, max_exp))

    if in_downtrend:
        return {"TQQQ": 0.0, "SQQQ": weight}
    else:
        return {"TQQQ": weight, "SQQQ": 0.0}

def classify_phase(df: pd.DataFrame, fast: int, bb_p: int, bb_std: float) -> str:
    """
    Returns one of: 'MOMENTUM', 'ACCUMULATE', 'MEANREVERT'
      - MOMENTUM: close > upper band AND close > fast MA AND fast MA slope up
      - ACCUMULATE: close >= fast MA (not MOMENTUM)
      - MEANREVERT: otherwise
    """
    sma_fast = compute_sma(df, fast)
    upper, _ = compute_bbands(df, bb_p, bb_std)
    c = df["close"].iloc[-1]
    mom = (c > upper.iloc[-1])
    # confirmations
    if mom and c > sma_fast.iloc[-1]:
        if len(sma_fast) >= 2 and pd.notna(sma_fast.iloc[-2]) and sma_fast.iloc[-1] > sma_fast.iloc[-2]:
            return "MOMENTUM"
    # accumulate vs mean-revert
    return "ACCUMULATE" if c >= sma_fast.iloc[-1] else "MEANREVERT"
