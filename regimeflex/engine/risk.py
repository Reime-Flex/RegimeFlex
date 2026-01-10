from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd

from regimeflex.engine.indicators import atr, realized_vol_pct_change

# Shadow testing imports
from regimeflex.engine.core_logic import (
    calculate_base_volatility_core,
    calculate_regime_vol_adjustment_core,
    calculate_decay_adjustment_core,
    calculate_position_size_core
)
from regimeflex.engine.shadow_test import compare_floats, log_shadow_mismatch

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
                          cfg: RiskConfig,
                          decay_stats: dict | None = None) -> tuple[float, str]:
    """
    Returns (target_position_dollars, note).
    Implements:
      size = (risk_budget * regime_vol_adjust * decay_adjust) / base_vol
      with extra conservatism and max_position cap.
      
    Args:
        inputs: Risk inputs
        close: Close price series
        high: High price series
        low: Low price series
        cfg: Risk configuration
        decay_stats: Optional decay statistics dict from log_volatility_decay()
                    Expected keys: period_decay_pct, daily_tracking_error_bps
    """
    from regimeflex.engine.identity import RegimeFlexIdentity as RF
    
    # OLD CODE PATH
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

    # Priority 2: Leverage Decay Adjustment
    # Reduce position sizes by up to 30% if decay indicates choppy market
    decay_adjust = 1.0
    if decay_stats:
        # If decay is positive (underperforming), reduce size
        # Decay > 1% over 20 days suggests choppy regime
        period_decay = decay_stats.get("period_decay_pct", 0.0)
        if period_decay > 1.0:  # 1% decay threshold
            # Scale down by decay severity (max 30% reduction)
            # Formula: decay_adjust = max(0.7, 1.0 - (period_decay / 10.0))
            # Example: 2% decay → 1.0 - 0.2 = 0.8 (20% reduction)
            # Example: 5% decay → 1.0 - 0.5 = 0.5 (50% reduction, capped at 0.7 = 30% reduction)
            decay_adjust = max(0.7, 1.0 - (period_decay / 10.0))
            RF.print_log(
                f"🛡️ Decay adjustment: {decay_adjust:.2f} (decay={period_decay:.2f}% over 20d)",
                "RISK"
            )

    size = (inputs.equity * cfg.risk_budget_pct * regime_vol_adjust * decay_adjust) / base_vol

    # extra conservatism vs max_position_pct * 0.8
    max_cap = inputs.equity * (cfg.max_position_pct * 0.8)
    
    # Apply OPEX scaling to cap as well
    if getattr(inputs, "is_opex", False):
        max_cap = max_cap * 0.85
    
    target = min(size, max_cap)
    
    # SHADOW TEST: Compare with new core logic
    base_vol_new = calculate_base_volatility_core(close, high, low, cfg.atr_len)
    regime_vol_adjust_new = calculate_regime_vol_adjustment_core(inputs.vix, inputs.qqq_close, getattr(inputs, "is_opex", False))
    decay_adjust_new = calculate_decay_adjustment_core(decay_stats)
    position_size_result = calculate_position_size_core(
        equity=inputs.equity,
        base_vol=base_vol_new,
        risk_budget_pct=cfg.risk_budget_pct,
        regime_vol_adjust=regime_vol_adjust_new,
        decay_adjust=decay_adjust_new,
        max_position_pct=cfg.max_position_pct,
        is_opex=getattr(inputs, "is_opex", False)
    )
    
    # Compare results
    base_vol_match = compare_floats(base_vol, base_vol_new, field_name="base_vol")
    regime_adj_match = compare_floats(regime_vol_adjust, regime_vol_adjust_new, field_name="regime_vol_adjust")
    decay_adj_match = compare_floats(decay_adjust, decay_adjust_new, field_name="decay_adjust")
    target_match = compare_floats(float(target), position_size_result.target_dollars, field_name="target_dollars")
    
    errors = []
    if not base_vol_match.match:
        errors.append(base_vol_match.error_message or "")
    if not regime_adj_match.match:
        errors.append(regime_adj_match.error_message or "")
    if not decay_adj_match.match:
        errors.append(decay_adj_match.error_message or "")
    if not target_match.match:
        errors.append(target_match.error_message or "")
    
    if errors:
        log_shadow_mismatch(
            "dynamic_position_size",
            errors,
            {"base_vol": base_vol, "regime_adj": regime_vol_adjust, "decay_adj": decay_adjust, "target": float(target)},
            {"base_vol": base_vol_new, "regime_adj": regime_vol_adjust_new, "decay_adj": decay_adjust_new, "target": position_size_result.target_dollars}
        )

    return float(target), f"base_vol={base_vol:.4f}, adj={regime_vol_adjust:.2f}, decay_adj={decay_adjust:.2f}, cap={max_cap:.2f}"
