from __future__ import annotations
from dataclasses import dataclass

import pandas as pd

from .signals import detect_regime, trend_signal, mr_signal, RegimeState
from .risk import RiskConfig, RiskInputs, circuit_breakers, dynamic_position_size
from .regime_buffer import detect_regime_with_hysteresis, load_regime_state, save_regime_state
from .bar_completeness import get_safe_price
from .indicators import sma
from .identity import RegimeFlexIdentity as RF

# Shadow testing imports
from .core_logic import (
    get_safe_price_core,
    detect_regime_with_hysteresis_core,
    calculate_base_volatility_core,
    calculate_regime_vol_adjustment_core,
    calculate_decay_adjustment_core,
    calculate_position_size_core,
    circuit_breakers_core
)
from .shadow_test import (
    compare_floats,
    compare_bools,
    compare_strings,
    log_shadow_mismatch
)

@dataclass(frozen=True)
class TargetExposure:
    symbol: str
    direction: str         # "LONG", "SHORT", or "FLAT"
    dollars: float         # desired notional in $
    shares: float          # desired shares (signed for direction)
    notes: str

def choose_active_symbol(regime: RegimeState, bull_symbol="QQQ", bear_symbol="PSQ") -> str:
    return bull_symbol if regime.bull else bear_symbol

def combine_signals(trend_entry: bool, trend_exit: bool, mr_dir: str, mr_entry: bool) -> str:
    """
    Priority: Trend defines core bias (LONG or FLAT).
    MR overlays only if aligned with trend bias in bull regime,
    or provides short bias in bear regime via PSQ.
    Output: "LONG" | "SHORT" | "FLAT"
    """
    # Trend bias
    trend_bias = "LONG" if trend_entry and not trend_exit else "FLAT"

    if trend_bias == "LONG":
        # allow MR to confirm long only
        if mr_entry and mr_dir == "LONG":
            return "LONG"
        return "LONG"  # trend alone ok
    else:
        # No long trend; in bear regime MR may short (via PSQ)
        if mr_entry and mr_dir == "SHORT":
            return "SHORT"
        return "FLAT"

def compute_target_exposure(
    qqq: pd.DataFrame,
    psq: pd.DataFrame,
    equity: float,
    vix: float | None = None,
    cfg: RiskConfig | None = None,
    is_fomc_window: bool = False,
    is_opex_day: bool = False,
    decay_stats: dict | None = None,
) -> TargetExposure:
    cfg = cfg or RiskConfig()

    # 1) Regime with hysteresis (prevent flashing signals)
    regime_state = load_regime_state()
    slow_ma_series = sma(qqq["close"], 200)
    
    # Get safe price for regime detection (prevent look-ahead bias)
    # OLD CODE PATH
    qqq_safe_price, qqq_price_safe, qqq_price_reason = get_safe_price(
        qqq, use_t1_if_incomplete=True, fallback_to_last=False
    )
    
    # SHADOW TEST: Compare with new core logic
    safe_price_result = get_safe_price_core(
        qqq, use_t1_if_incomplete=True, fallback_to_last=False
    )
    price_match = compare_floats(qqq_safe_price, safe_price_result.price, field_name="qqq_safe_price")
    safe_match = compare_bools(qqq_price_safe, safe_price_result.is_safe, field_name="qqq_price_safe")
    if not price_match.match or not safe_match.match:
        log_shadow_mismatch(
            "get_safe_price (regime detection)",
            [price_match.error_message or "", safe_match.error_message or ""],
            {"price": qqq_safe_price, "is_safe": qqq_price_safe, "reason": qqq_price_reason},
            {"price": safe_price_result.price, "is_safe": safe_price_result.is_safe, "reason": safe_price_result.reason}
        )
    
    if not qqq_price_safe or qqq_safe_price <= 0:
        RF.print_log(f"⚠️ Cannot determine safe price for regime: {qqq_price_reason}", "RISK")
        return TargetExposure(
            symbol="QQQ", direction="FLAT", dollars=0.0, shares=0.0,
            notes=f"Price safety check failed: {qqq_price_reason}"
        )
    
    slow_ma_val = float(slow_ma_series.iloc[-1]) if pd.notna(slow_ma_series.iloc[-1]) else 0.0
    
    if slow_ma_val <= 0:
        RF.print_log("⚠️ Invalid SMA for regime detection", "RISK")
        return TargetExposure(
            symbol="QQQ", direction="FLAT", dollars=0.0, shares=0.0,
            notes="Invalid SMA value"
        )
    
    # Use hysteresis for regime detection
    # OLD CODE PATH
    is_bull, regime_reason, new_regime_state = detect_regime_with_hysteresis(
        qqq_safe_price,
        slow_ma_val,
        regime_state,
        buffer_pct=0.02,  # 2% buffer band
        confirmation_days=2  # Require 2 days to flip
    )
    
    # SHADOW TEST: Compare with new core logic
    is_bull_new, regime_reason_new, new_regime_state_new = detect_regime_with_hysteresis_core(
        qqq_safe_price,
        slow_ma_val,
        regime_state,
        buffer_pct=0.02,
        confirmation_days=2
    )
    bull_match = compare_bools(is_bull, is_bull_new, field_name="is_bull")
    reason_match = compare_strings(regime_reason, regime_reason_new, field_name="regime_reason", case_sensitive=False)
    if not bull_match.match or not reason_match.match:
        log_shadow_mismatch(
            "detect_regime_with_hysteresis",
            [bull_match.error_message or "", reason_match.error_message or ""],
            {"is_bull": is_bull, "reason": regime_reason, "state": new_regime_state},
            {"is_bull": is_bull_new, "reason": regime_reason_new, "state": new_regime_state_new}
        )
    
    save_regime_state(new_regime_state)
    RF.print_log(f"Regime (with hysteresis): {regime_reason}", "INFO")
    
    # Get base regime for other calculations
    regime_base = detect_regime(qqq["close"])
    regime = RegimeState(bull=is_bull, vix=vix, qqq_rvol_20=regime_base.qqq_rvol_20)

    # 2) Signals
    t_sig = trend_signal(qqq, regime, vix_max=30.0, qqq_vol_50d_max=0.40)
    active_df = qqq if regime.bull else psq
    m_sig = mr_signal(active_df, regime, z_len=20, vol_confirm_mult=1.2)

    # 3) Direction decision
    direction = combine_signals(t_sig.entry, t_sig.exit, m_sig.direction, m_sig.entry)
    symbol = "QQQ" if regime.bull else "PSQ"
    df = active_df

    # 4) Get safe price for position sizing (prevent look-ahead bias)
    # OLD CODE PATH
    safe_price, price_safe, price_reason = get_safe_price(
        df, use_t1_if_incomplete=True, fallback_to_last=False
    )
    
    # SHADOW TEST: Compare with new core logic
    safe_price_result_sizing = get_safe_price_core(
        df, use_t1_if_incomplete=True, fallback_to_last=False
    )
    price_match_sizing = compare_floats(safe_price, safe_price_result_sizing.price, field_name="safe_price_sizing")
    safe_match_sizing = compare_bools(price_safe, safe_price_result_sizing.is_safe, field_name="price_safe_sizing")
    if not price_match_sizing.match or not safe_match_sizing.match:
        log_shadow_mismatch(
            "get_safe_price (position sizing)",
            [price_match_sizing.error_message or "", safe_match_sizing.error_message or ""],
            {"price": safe_price, "is_safe": price_safe, "reason": price_reason},
            {"price": safe_price_result_sizing.price, "is_safe": safe_price_result_sizing.is_safe, "reason": safe_price_result_sizing.reason}
        )
    
    if not price_safe or safe_price <= 0:
        RF.print_log(f"⚠️ Cannot determine safe price for sizing: {price_reason}", "RISK")
        return TargetExposure(
            symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
            notes=f"Price safety check failed: {price_reason}"
        )
    
    RF.print_log(f"Using safe price for sizing: {price_reason}", "INFO")

    # 5) Circuit breakers & sizing (QQQ close drives risk)
    inputs = RiskInputs(
        equity=float(equity),
        price=safe_price,  # Use verified safe price
        vix=vix,
        qqq_close=qqq["close"],
        is_fomc_window=is_fomc_window,
        is_opex=is_opex_day,
    )
    # OLD CODE PATH
    blocked, reason = circuit_breakers(inputs, cfg)
    
    # SHADOW TEST: Compare with new core logic
    blocked_new, reason_new = circuit_breakers_core(
        vix=vix,
        qqq_close=qqq["close"],
        vix_hard=cfg.vix_hard,
        qqq_20d_vol_max=cfg.qqq_20d_vol_max,
        is_fomc_window=is_fomc_window,
        is_opex=is_opex_day
    )
    blocked_match = compare_bools(blocked, blocked_new, field_name="circuit_breaker_blocked")
    reason_match_cb = compare_strings(reason, reason_new, field_name="circuit_breaker_reason", case_sensitive=False)
    if not blocked_match.match or not reason_match_cb.match:
        log_shadow_mismatch(
            "circuit_breakers",
            [blocked_match.error_message or "", reason_match_cb.error_message or ""],
            {"blocked": blocked, "reason": reason},
            {"blocked": blocked_new, "reason": reason_new}
        )
    
    if blocked or direction == "FLAT":
        return TargetExposure(symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
                              notes=f"{'BLOCKED: ' + reason if blocked else 'Direction FLAT'} | "
                                    f"trend(entry={t_sig.entry}, exit={t_sig.exit}), mr({m_sig.direction}, entry={m_sig.entry})")

    # Pass decay_stats for the current symbol to position sizing
    symbol_decay = decay_stats.get(symbol) if decay_stats else None
    # OLD CODE PATH
    dollars, note = dynamic_position_size(
        inputs, df["close"], df["high"], df["low"], cfg,
        decay_stats=symbol_decay
    )
    
    # SHADOW TEST: Compare with new core logic
    base_vol_new = calculate_base_volatility_core(df["close"], df["high"], df["low"], cfg.atr_len)
    regime_vol_adjust_new = calculate_regime_vol_adjustment_core(vix, qqq["close"], is_opex_day)
    decay_adjust_new = calculate_decay_adjustment_core(symbol_decay)
    position_size_result = calculate_position_size_core(
        equity=float(equity),
        base_vol=base_vol_new,
        risk_budget_pct=cfg.risk_budget_pct,
        regime_vol_adjust=regime_vol_adjust_new,
        decay_adjust=decay_adjust_new,
        max_position_pct=cfg.max_position_pct,
        is_opex=is_opex_day
    )
    dollars_match = compare_floats(dollars, position_size_result.target_dollars, field_name="position_dollars")
    if not dollars_match.match:
        log_shadow_mismatch(
            "dynamic_position_size",
            [dollars_match.error_message or ""],
            {"dollars": dollars, "note": note},
            {"dollars": position_size_result.target_dollars, "note": position_size_result.note}
        )
    
    if dollars <= 0:
        return TargetExposure(symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
                              notes=f"Zero size | {note}")

    # 5) Shares (signed)
    sign = 1 if direction == "LONG" else -1
    shares = sign * (dollars / inputs.price)

    return TargetExposure(symbol=symbol, direction=direction, dollars=dollars, shares=shares,
                          notes=f"{note} | regime={'BULL' if regime.bull else 'BEAR'}; "
                                f"trend(entry={t_sig.entry}, exit={t_sig.exit}); "
                                f"mr(dir={m_sig.direction}, entry={m_sig.entry}, z={m_sig.z})")
