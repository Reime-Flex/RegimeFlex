"""
Core Logic Module - Single Source of Truth

This module centralizes critical trading logic to eliminate duplication:
- Regime calculation (MA/RSI/VIX)
- Order sizing mathematics
- Data validation & cleaning

All functions are pure and deterministic for shadow testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import math
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from regimeflex.engine.indicators import sma, rolling_std, realized_vol_pct_change, atr
from regimeflex.engine.signals import RegimeState, TrendSignal, MRSignal
# Note: RiskConfig and RiskInputs imported via TYPE_CHECKING to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from regimeflex.engine.risk import RiskConfig, RiskInputs


# ============================================================================
# DATA VALIDATION & CLEANING
# ============================================================================

@dataclass(frozen=True)
class SafePriceResult:
    """Result of safe price calculation."""
    price: float
    is_safe: bool
    reason: str


def is_bar_complete(bar_date: pd.Timestamp | datetime, current_time: datetime | None = None) -> bool:
    """
    Check if a bar is complete (not from current trading day).
    
    Args:
        bar_date: Date/timestamp of the bar
        current_time: Current time (defaults to now if None)
    
    Returns:
        True if bar is from a completed day
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Convert bar_date to date
    if isinstance(bar_date, pd.Timestamp):
        bar_date_dt = bar_date.to_pydatetime()
        if bar_date_dt.tzinfo is None:
            bar_date_dt = bar_date_dt.replace(tzinfo=timezone.utc)
        bar_date_only = bar_date_dt.date()
    elif isinstance(bar_date, datetime):
        if bar_date.tzinfo is None:
            bar_date = bar_date.replace(tzinfo=timezone.utc)
        bar_date_only = bar_date.date()
    else:
        bar_date_only = bar_date
    
    current_date = current_time.date()
    
    # Bar is complete if it's from yesterday or earlier
    return bar_date_only < current_date


def get_safe_price_core(
    df: pd.DataFrame,
    use_t1_if_incomplete: bool = True,
    fallback_to_last: bool = False,
    current_time: datetime | None = None
) -> SafePriceResult:
    """
    Get a safe price from DataFrame, ensuring no look-ahead bias.
    
    This is the centralized version of get_safe_price() logic.
    
    Args:
        df: DataFrame with datetime index and 'close' column
        use_t1_if_incomplete: If True, use T-1 bar if last bar is incomplete
        fallback_to_last: If True, fall back to last bar if T-1 unavailable
        current_time: Current time for completeness check (defaults to now)
    
    Returns:
        SafePriceResult with price, safety flag, and reason
    """
    if df is None or df.empty or len(df) == 0:
        return SafePriceResult(price=0.0, is_safe=False, reason="Empty DataFrame")
    
    last_bar_date = df.index[-1]
    last_price = float(df["close"].iloc[-1])
    
    # Check if last bar is complete
    if is_bar_complete(last_bar_date, current_time):
        return SafePriceResult(
            price=last_price,
            is_safe=True,
            reason=f"Using last bar price ${last_price:.2f} (complete)"
        )
    
    # Last bar is incomplete - use T-1 if available
    if use_t1_if_incomplete and len(df) > 1:
        t1_price = float(df["close"].iloc[-2])
        return SafePriceResult(
            price=t1_price,
            is_safe=True,
            reason=f"Using T-1 bar price ${t1_price:.2f} (last bar incomplete)"
        )
    
    # Fallback to last bar if allowed
    if fallback_to_last:
        return SafePriceResult(
            price=last_price,
            is_safe=False,
            reason=f"Using last bar price ${last_price:.2f} (incomplete, fallback)"
        )
    
    return SafePriceResult(
        price=0.0,
        is_safe=False,
        reason="Last bar incomplete and T-1 unavailable"
    )


def validate_bar_hygiene_core(
    symbol: str,
    df: pd.DataFrame,
    checks: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Validate bar data hygiene (OHLC consistency, volume, gaps).
    
    Centralized version of validate_last_bar() logic.
    
    Args:
        symbol: Symbol name for logging
        df: DataFrame with open, high, low, close, volume columns
        checks: Configuration dict with check flags
    
    Returns:
        Tuple of (is_valid, reason)
    """
    if df is None or len(df) == 0:
        return False, "empty_df"
    
    r = df.iloc[-1]
    try:
        o = float(r["open"])
        h = float(r["high"])
        l = float(r["low"])
        c = float(r["close"])
        v = float(r["volume"])
    except Exception:
        return False, "missing_fields"
    
    # Positive prices
    if checks.get("positive_prices", True):
        if not (o > 0 and h > 0 and l > 0 and c > 0):
            return False, "non_positive_price"
    
    # Monotonic OHLC
    if checks.get("ohlc_monotonic", True):
        lo_ref = min(o, c)
        hi_ref = max(o, c)
        if not (l <= lo_ref + 1e-12 and h + 1e-12 >= hi_ref and l <= h):
            return False, "ohlc_monotonic_fail"
    
    # Non-negative volume
    if checks.get("non_negative_volume", True):
        if v < 0:
            return False, "negative_volume"
    
    # Max gap vs prev close
    mgp = checks.get("max_gap_pct", None)
    if mgp is not None and len(df) >= 2:
        pc = float(df["close"].iloc[-2])
        if pc > 0:
            gap = abs(c - pc) / pc
            if gap > float(mgp):
                return False, f"gap_gt_{mgp:.2f}"
    
    return True, "OK"


# ============================================================================
# REGIME CALCULATION LOGIC
# ============================================================================

@dataclass(frozen=True)
class RegimeCalculationResult:
    """Result of regime calculation."""
    is_bull: bool
    regime_state: Dict[str, Any]
    reason: str
    slow_ma_value: float
    qqq_safe_price: float


def detect_regime_core(
    qqq_close: pd.Series,
    slow: int = 200,
    require_complete_bar: bool = True,
    current_time: datetime | None = None
) -> RegimeState:
    """
    Detect market regime (Bull/Bear) based on price vs moving average.
    
    Centralized version of detect_regime() logic.
    
    Args:
        qqq_close: QQQ close price series
        slow: Period for slow MA (default 200)
        require_complete_bar: If True, avoid using incomplete current-day bars
        current_time: Current time for completeness check
    
    Returns:
        RegimeState with bull flag and volatility metrics
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Handle incomplete bars
    qqq_close_to_use = qqq_close
    if require_complete_bar and len(qqq_close) > 0:
        last_bar_date = qqq_close.index[-1]
        today = current_time.date()
        
        if hasattr(last_bar_date, 'date'):
            bar_date = last_bar_date.date() if hasattr(last_bar_date, 'tz') else last_bar_date
            if isinstance(bar_date, datetime):
                bar_date = bar_date.date()
            if bar_date >= today:
                # Use T-1 bar instead
                if len(qqq_close) > 1:
                    qqq_close_to_use = qqq_close.iloc[:-1]
                # else: cannot truncate, use as-is
    
    # Calculate slow MA
    slow_ma = sma(qqq_close_to_use, slow)
    close_val = qqq_close_to_use.iloc[-1]
    ma_val = slow_ma.iloc[-1]
    
    # Use epsilon comparison to prevent floating-point noise
    EPSILON = 1e-6
    bull = bool((close_val - ma_val) > EPSILON if pd.notna(ma_val) else False)
    
    # Calculate realized volatility
    rvol20 = realized_vol_pct_change(qqq_close_to_use, 20).iloc[-1] if qqq_close_to_use.size else None
    
    return RegimeState(
        bull=bull,
        vix=None,  # VIX provided separately
        qqq_rvol_20=float(rvol20) if pd.notna(rvol20) else None
    )


def detect_regime_with_hysteresis_core(
    qqq_close: float,
    slow_ma: float,
    current_regime_state: Dict[str, Any],
    buffer_pct: float = 0.02,
    confirmation_days: int = 2
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Detect regime with hysteresis to prevent signal flashing.
    
    Centralized version of detect_regime_with_hysteresis() logic.
    Matches original implementation exactly.
    
    Args:
        qqq_close: QQQ close price (safe price from complete bar)
        slow_ma: Slow MA value (200-day)
        current_regime_state: Current regime state dict
        buffer_pct: Buffer percentage around MA (default 0.02 = 2%)
        confirmation_days: Days required to confirm regime flip
    
    Returns:
        Tuple of (is_bull, reason, new_regime_state)
    """
    if slow_ma <= 0:
        return False, "Invalid SMA", current_regime_state
    
    upper_band = slow_ma * (1 + buffer_pct)
    lower_band = slow_ma * (1 - buffer_pct)
    
    last_confirmed = current_regime_state.get("confirmed_regime")
    consecutive = current_regime_state.get("consecutive_days", 0)
    
    # Determine raw signal
    if qqq_close > upper_band:
        raw_signal = True
        position = "ABOVE_UPPER"
    elif qqq_close < lower_band:
        raw_signal = False
        position = "BELOW_LOWER"
    else:
        # Within buffer zone - maintain current regime
        raw_signal = last_confirmed if last_confirmed is not None else True
        position = "IN_BUFFER"
    
    # Apply confirmation logic
    # Note: Original code uses boolean True/False for confirmed_regime, not strings
    if last_confirmed is None:
        # First run: accept raw signal
        new_state = {
            "confirmed_regime": raw_signal,  # Boolean, not string
            "since_date": datetime.now(timezone.utc).isoformat(),
            "consecutive_days": 1
        }
        return raw_signal, f"Initial regime set: {position}", new_state
    
    # Convert confirmed_regime to bool for comparison (handle both bool and string formats)
    if isinstance(last_confirmed, str):
        confirmed_bool = (last_confirmed == "BULL")
    else:
        confirmed_bool = bool(last_confirmed)
    
    if raw_signal == confirmed_bool:
        # Regime confirmed, reset counter
        new_state = {
            "confirmed_regime": last_confirmed,  # Keep original format
            "since_date": current_regime_state.get("since_date"),
            "consecutive_days": 0
        }
        return confirmed_bool, f"Regime confirmed: {position}", new_state
    
    # Signal differs from confirmed regime
    if position == "IN_BUFFER":
        # Don't count buffer zone days toward flip
        return confirmed_bool, f"In buffer zone, maintaining {last_confirmed}", current_regime_state
    
    # Outside buffer and different from confirmed
    consecutive += 1
    if consecutive >= confirmation_days:
        # Flip confirmed
        new_state = {
            "confirmed_regime": raw_signal,  # Boolean, not string
            "since_date": datetime.now(timezone.utc).isoformat(),
            "consecutive_days": 0
        }
        return raw_signal, f"Regime FLIP after {confirmation_days} days: {position}", new_state
    else:
        # Not enough days yet
        new_state = {
            "confirmed_regime": last_confirmed,  # Keep original format
            "since_date": current_regime_state.get("since_date"),
            "consecutive_days": consecutive
        }
        return confirmed_bool, f"Pending flip ({consecutive}/{confirmation_days}): {position}", new_state


# ============================================================================
# ORDER SIZING MATHEMATICS
# ============================================================================

@dataclass(frozen=True)
class PositionSizeResult:
    """Result of position sizing calculation."""
    target_dollars: float
    note: str
    base_vol: float
    regime_vol_adjust: float
    decay_adjust: float
    max_cap: float


def calculate_base_volatility_core(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    atr_len: int = 14
) -> float:
    """
    Calculate base volatility (ATR/price).
    
    Centralized version of _base_vol() logic.
    
    Args:
        close: Close price series
        high: High price series
        low: Low price series
        atr_len: ATR period (default 14)
    
    Returns:
        Base volatility (ATR/close)
    """
    a = atr(high, low, close, n=atr_len).iloc[-1]
    return float(a / close.iloc[-1])


def calculate_regime_vol_adjustment_core(
    vix: Optional[float],
    qqq_close: pd.Series,
    is_opex: bool = False
) -> float:
    """
    Calculate regime volatility adjustment factor.
    
    Centralized version of regime_vol_adjust calculation.
    
    Args:
        vix: VIX value (None if unavailable)
        qqq_close: QQQ close price series for realized vol
        is_opex: Whether it's options expiration day
    
    Returns:
        Adjustment factor (0.0 to 1.0)
    """
    regime_vol_adjust = 1.0
    
    # VIX adjustment
    if vix is not None and vix > 25:
        regime_vol_adjust = 0.7
    
    # Realized vol adjustment
    rvol20 = realized_vol_pct_change(qqq_close, 20).iloc[-1]
    if pd.notna(rvol20) and float(rvol20) > 0.25:
        regime_vol_adjust = min(regime_vol_adjust, 0.5)
    
    # OPEX conservatism
    if is_opex:
        regime_vol_adjust = min(regime_vol_adjust, 0.85)
    
    return regime_vol_adjust


def calculate_decay_adjustment_core(
    decay_stats: Optional[Dict[str, Any]]
) -> float:
    """
    Calculate leverage decay adjustment factor.
    
    Centralized version of decay_adjust calculation.
    
    Args:
        decay_stats: Decay statistics dict with period_decay_pct
    
    Returns:
        Adjustment factor (0.7 to 1.0)
    """
    decay_adjust = 1.0
    
    if decay_stats:
        period_decay = decay_stats.get("period_decay_pct", 0.0)
        if period_decay > 1.0:  # 1% decay threshold
            # Scale down by decay severity (max 30% reduction)
            # Formula: decay_adjust = max(0.7, 1.0 - (period_decay / 10.0))
            decay_adjust = max(0.7, 1.0 - (period_decay / 10.0))
    
    return decay_adjust


def calculate_position_size_core(
    equity: float,
    base_vol: float,
    risk_budget_pct: float,
    regime_vol_adjust: float,
    decay_adjust: float,
    max_position_pct: float,
    is_opex: bool = False
) -> PositionSizeResult:
    """
    Calculate target position size in dollars.
    
    Centralized version of dynamic_position_size() core math.
    
    Formula: size = (equity * risk_budget_pct * regime_vol_adjust * decay_adjust) / base_vol
    Capped at: equity * max_position_pct * 0.8 * (0.85 if OPEX)
    
    Args:
        equity: Account equity
        base_vol: Base volatility (ATR/price)
        risk_budget_pct: Risk budget percentage (e.g., 0.015 = 1.5%)
        regime_vol_adjust: Regime volatility adjustment (0.0 to 1.0)
        decay_adjust: Decay adjustment (0.7 to 1.0)
        max_position_pct: Maximum position percentage (e.g., 0.60 = 60%)
        is_opex: Whether it's options expiration day
    
    Returns:
        PositionSizeResult with target dollars and calculation details
    """
    if base_vol <= 0 or math.isnan(base_vol):
        return PositionSizeResult(
            target_dollars=0.0,
            note="Invalid base_vol",
            base_vol=base_vol,
            regime_vol_adjust=regime_vol_adjust,
            decay_adjust=decay_adjust,
            max_cap=0.0
        )
    
    # Calculate base size
    size = (equity * risk_budget_pct * regime_vol_adjust * decay_adjust) / base_vol
    
    # Calculate max cap
    max_cap = equity * (max_position_pct * 0.8)
    
    # Apply OPEX scaling to cap
    if is_opex:
        max_cap = max_cap * 0.85
    
    # Apply cap
    target = min(size, max_cap)
    
    note = (
        f"base_vol={base_vol:.4f}, "
        f"adj={regime_vol_adjust:.2f}, "
        f"decay_adj={decay_adjust:.2f}, "
        f"cap={max_cap:.2f}"
    )
    
    return PositionSizeResult(
        target_dollars=float(target),
        note=note,
        base_vol=base_vol,
        regime_vol_adjust=regime_vol_adjust,
        decay_adjust=decay_adjust,
        max_cap=max_cap
    )


def circuit_breakers_core(
    vix: Optional[float],
    qqq_close: pd.Series,
    vix_hard: float = 35.0,
    qqq_20d_vol_max: float = 0.40,
    is_fomc_window: bool = False,
    is_opex: bool = False
) -> Tuple[bool, str]:
    """
    Check circuit breakers (hard blocks).
    
    Centralized version of circuit_breakers() logic.
    
    Args:
        vix: VIX value (None if unavailable)
        qqq_close: QQQ close price series
        vix_hard: Hard VIX threshold (default 35.0)
        qqq_20d_vol_max: Max 20-day realized vol (default 0.40 = 40%)
        is_fomc_window: Whether in FOMC blackout window
        is_opex: Whether it's options expiration (caution only, not blocked)
    
    Returns:
        Tuple of (is_blocked, reason)
    """
    # Hard VIX block
    if vix is not None and vix >= vix_hard:
        return True, f"VIX hard block (≥ {vix_hard})"
    
    # Realized vol block
    rvol20 = realized_vol_pct_change(qqq_close, 20).iloc[-1]
    if pd.notna(rvol20) and float(rvol20) > qqq_20d_vol_max:
        return True, f"Realized vol 20d block (> {qqq_20d_vol_max:.2f})"
    
    # FOMC blackout
    if is_fomc_window:
        return True, "FOMC blackout"
    
    # OPEX is caution only (not blocked)
    if is_opex:
        return False, "OPEX caution (size scaling recommended)"
    
    return False, "OK"

