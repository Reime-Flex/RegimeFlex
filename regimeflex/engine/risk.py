from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd

from .indicators import atr, realized_vol_pct_change

@dataclass(frozen=True)
class RiskConfig:
    # position sizing
    risk_budget_pct: float = 0.015
    atr_len: int = 14
    max_position_pct: float = 0.60

    # regime adjustments
    vix_soft: float = 25.0
    vix_hard: float = 35.0
    qqq_20d_vol_max: float = 0.40

    # circuit breakers
    fomc_blackout_days: tuple[int, int] = (-1, 1)   # day before & after
    options_expiry_caution: bool = True
    earnings_blackout: bool = False  # ETFs ignore

@dataclass(frozen=True)
class RiskInputs:
    equity: float                # account equity $
    price: float                 # current instrument price
    vix: float | None            # latest VIX (None allowed)
    qqq_close: pd.Series         # for realized vol calc
    is_fomc_window: bool = False
    is_opex: bool = False

def _base_vol(close: pd.Series, high: pd.Series, low: pd.Series, atr_len: int) -> float:
    a = atr(high, low, close, n=atr_len).iloc[-1]
    return float(a / close.iloc[-1])

def circuit_breakers(inputs: RiskInputs, cfg: RiskConfig) -> tuple[bool, str]:
    """Returns (blocked?, reason)."""
    # Hard VIX block
    if inputs.vix is not None and inputs.vix >= cfg.vix_hard:
        return True, f"VIX hard block (≥ {cfg.vix_hard})"

    # Realized vol block
    rvol20 = realized_vol_pct_change(inputs.qqq_close, 20).iloc[-1]
    if pd.notna(rvol20) and float(rvol20) > cfg.qqq_20d_vol_max:
        return True, f"Realized vol 20d block (> {cfg.qqq_20d_vol_max:.2f})"

    # Event blackouts
    if inputs.is_fomc_window:
        return True, f"FOMC blackout {cfg.fomc_blackout_days}"

    # OPEX is caution only (caller may scale size)
    if inputs.is_opex:
        return False, "OPEX caution (size scaling recommended)"

    return False, "OK"

def dynamic_position_size(inputs: RiskInputs,
                          close: pd.Series, high: pd.Series, low: pd.Series,
                          cfg: RiskConfig) -> tuple[float, str]:
    """
    Returns (target_position_dollars, note).
    Implements:
      size = (risk_budget * regime_vol_adjust) / base_vol
      with extra conservatism and max_position cap.
    """
    base_vol = _base_vol(close, high, low, cfg.atr_len)  # ATR/price
    if base_vol <= 0 or math.isnan(base_vol):
        return 0.0, "Invalid base_vol"

    # Regime adjustments (soft VIX + realized vol)
    regime_vol_adjust = 1.0
    if inputs.vix is not None and inputs.vix > 25:
        regime_vol_adjust = 0.7
    rvol20 = realized_vol_pct_change(inputs.qqq_close, 20).iloc[-1]
    if pd.notna(rvol20) and float(rvol20) > 0.25:
        regime_vol_adjust = min(regime_vol_adjust, 0.5)

    # extra conservatism for OPEX day
    if getattr(inputs, "is_opex", False):
        regime_vol_adjust = min(regime_vol_adjust, 0.85)

    size = (inputs.equity * cfg.risk_budget_pct * regime_vol_adjust) / base_vol

    # extra conservatism vs max_position_pct * 0.8
    max_cap = inputs.equity * (cfg.max_position_pct * 0.8)
    
    # Apply OPEX scaling to cap as well
    if getattr(inputs, "is_opex", False):
        max_cap = max_cap * 0.85
    
    target = min(size, max_cap)

    return float(target), f"base_vol={base_vol:.4f}, adj={regime_vol_adjust:.2f}, cap={max_cap:.2f}"
