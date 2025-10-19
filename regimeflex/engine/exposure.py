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

def exposure_allocator(df: pd.DataFrame) -> dict:
    """
    Returns desired exposure weights for TQQQ and SQQQ based on
    trend direction, extension, and Bollinger momentum.
    """
    cfg = Config(".")._load_yaml("config/exposure.yaml")
    fast, slow = cfg["trend"]["fast_ma"], cfg["trend"]["slow_ma"]
    ext_factor = cfg["weights"]["extension_factor"]
    bb_p, bb_std = cfg["weights"]["bb_period"], cfg["weights"]["bb_std"]
    max_exp, min_exp = cfg["weights"]["max_exposure_pct"], cfg["weights"]["min_exposure_pct"]

    sma_fast = compute_sma(df, fast).iloc[-1]
    sma_slow = compute_sma(df, slow).iloc[-1]
    close = df["close"].iloc[-1]

    upper, lower = compute_bbands(df, bb_p, bb_std)
    upper_now = upper.iloc[-1]
    lower_now = lower.iloc[-1]

    in_momentum = close > upper_now
    in_downtrend = sma_fast < sma_slow
    ext = ndx_extension(df, slow)

    # base weight
    base = max(min(max_exp, cfg["weights"]["base_risk"]), 0.0)

    # reduce exposure if highly extended
    adj = np.exp(-ext_factor * abs(ext))
    weight = base * adj

    if in_downtrend:
        return {"TQQQ": 0.0, "SQQQ": weight}
    elif in_momentum:
        return {"TQQQ": min(weight * 1.3, max_exp), "SQQQ": 0.0}
    else:
        return {"TQQQ": weight, "SQQQ": 0.0}
