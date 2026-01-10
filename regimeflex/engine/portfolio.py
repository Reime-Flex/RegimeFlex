from __future__ import annotations
from dataclasses import dataclass

import pandas as pd

from .signals import detect_regime, trend_signal, mr_signal, RegimeState
from .risk import RiskConfig, RiskInputs, circuit_breakers, dynamic_position_size
from .regime_buffer import detect_regime_with_hysteresis, load_regime_state, save_regime_state
from .bar_completeness import get_safe_price
from .indicators import sma
from .identity import RegimeFlexIdentity as RF

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
    qqq_safe_price, qqq_price_safe, qqq_price_reason = get_safe_price(
        qqq, use_t1_if_incomplete=True, fallback_to_last=False
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
    is_bull, regime_reason, new_regime_state = detect_regime_with_hysteresis(
        qqq_safe_price,
        slow_ma_val,
        regime_state,
        buffer_pct=0.02,  # 2% buffer band
        confirmation_days=2  # Require 2 days to flip
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
    safe_price, price_safe, price_reason = get_safe_price(
        df, use_t1_if_incomplete=True, fallback_to_last=False
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
    blocked, reason = circuit_breakers(inputs, cfg)
    if blocked or direction == "FLAT":
        return TargetExposure(symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
                              notes=f"{'BLOCKED: ' + reason if blocked else 'Direction FLAT'} | "
                                    f"trend(entry={t_sig.entry}, exit={t_sig.exit}), mr({m_sig.direction}, entry={m_sig.entry})")

    # Pass decay_stats for the current symbol to position sizing
    symbol_decay = decay_stats.get(symbol) if decay_stats else None
    dollars, note = dynamic_position_size(
        inputs, df["close"], df["high"], df["low"], cfg,
        decay_stats=symbol_decay
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
