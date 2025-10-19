# engine/exposure_reason.py
from __future__ import annotations
import pandas as pd
from .config import Config
from .exposure import compute_sma, compute_bbands, ndx_extension, _realized_vol  # uses same math as allocator

def compute_exposure_diagnostics(df: pd.DataFrame) -> dict:
    """
    Mirrors the allocator's inputs to summarize 'why' a given weight was chosen.
    Does NOT change any sizing; read-only diagnostics.
    """
    exp = Config(".")._load_yaml("config/exposure.yaml")
    fast, slow = exp["trend"]["fast_ma"], exp["trend"]["slow_ma"]
    bb_p, bb_std = exp["weights"]["bb_period"], exp["weights"]["bb_std"]

    sma_fast = compute_sma(df, fast)
    sma_slow_val = compute_sma(df, slow).iloc[-1]
    close = float(df["close"].iloc[-1])
    upper, _ = compute_bbands(df, bb_p, bb_std)

    # States
    ext = ndx_extension(df, slow)                          # e.g., +0.07 = +7% above slow MA
    in_downtrend = sma_fast.iloc[-1] < sma_slow_val
    momentum = close > float(upper.iloc[-1])
    if momentum:
        # confirmations (Step 34 parity)
        momentum = momentum and (close > float(sma_fast.iloc[-1]))
        if len(sma_fast) >= 2 and pd.notna(sma_fast.iloc[-2]):
            momentum = momentum and (float(sma_fast.iloc[-1]) > float(sma_fast.iloc[-2]))

    # Realized vol
    vd = exp.get("vol_dampener", {}) or {}
    lookback = int(vd.get("lookback_days", 20))
    cap_rvol = float(vd.get("cap_rvol", 0.25))
    rvol = _realized_vol(df["close"], lookback)
    # implied scale used by allocator when rvol > cap
    if rvol <= cap_rvol:
        scale = 1.0
    else:
        x = min(2.0, rvol / max(cap_rvol, 1e-9))
        scale = max(float(vd.get("floor_scale", 0.60)), 2.0 - x)

    return {
        "ext": float(ext),
        "downtrend": bool(in_downtrend),
        "momentum": bool(momentum),
        "rvol": float(rvol),
        "rvol_cap": cap_rvol,
        "vol_scale": float(scale),
        "bb_p": bb_p,
        "bb_std": bb_std,
        "fast_ma": fast,
        "slow_ma": slow,
    }

def format_plan_reason(diag: dict, phase: str, guard_note: str) -> str:
    """
    Compact single line suitable for logs/telemetry/report.
    Example:
      ext=+6.8% mom=True rVol20=27.3% x0.74 phase=MOMENTUM caps=gross×0.769
    """
    ext_pct = f"{diag.get('ext',0.0)*100:+.1f}%"
    mom = "True" if diag.get("momentum") else "False"
    rvol_pct = f"{diag.get('rvol',0.0)*100:.1f}%"
    scale = diag.get("vol_scale", 1.0)
    caps = "OK" if guard_note in (None, "", "OK") else guard_note.replace("gross scaled×", "gross×")
    return f"ext={ext_pct} mom={mom} rVol{int(diag.get('fast_ma',20))}={rvol_pct} x{scale:.2f} phase={phase} caps={caps}"
