from __future__ import annotations
import math
import pandas as pd
import numpy as np

# Numerical stability constants
EPSILON = 1e-6  # Epsilon for floating-point comparisons
PRECISION = 6  # Decimal places for rounding

def sma(series: pd.Series, n: int, precision: int = PRECISION) -> pd.Series:
    """
    Simple Moving Average with precision rounding to prevent floating-point drift.
    
    Args:
        series: Price series
        n: Window size
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded SMA series
    """
    result = series.rolling(window=n, min_periods=n).mean()
    return result.round(precision)

def ema(series: pd.Series, n: int, precision: int = PRECISION) -> pd.Series:
    """
    Exponential Moving Average with precision rounding.
    
    Args:
        series: Price series
        n: Span
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded EMA series
    """
    result = series.ewm(span=n, adjust=False).mean()
    return result.round(precision)

def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14, precision: int = PRECISION) -> pd.Series:
    """
    Average True Range with precision rounding.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        n: Period
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded ATR series
    """
    tr = true_range(high, low, close)
    # Wilder's smoothing
    result = tr.ewm(alpha=1/n, adjust=False).mean()
    return result.round(precision)

def rolling_std(series: pd.Series, n: int, precision: int = PRECISION) -> pd.Series:
    """
    Rolling standard deviation with precision rounding.
    
    Args:
        series: Price series
        n: Window size
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded rolling std series
    """
    result = series.rolling(window=n, min_periods=n).std(ddof=0)
    return result.round(precision)

def realized_vol_pct_change(series: pd.Series, n: int = 20, annualization: int = 252, precision: int = PRECISION) -> pd.Series:
    """
    Annualized realized volatility of daily returns (as a fraction, not %) with precision rounding.
    
    Args:
        series: Price series
        n: Window size
        annualization: Trading days per year (default 252)
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded realized volatility series
    """
    rets = series.pct_change()
    vol = rets.rolling(n, min_periods=n).std(ddof=0) * np.sqrt(annualization)
    return vol.round(precision)

def zscore(series: pd.Series, n: int = 20, epsilon: float = EPSILON, precision: int = PRECISION) -> pd.Series:
    """
    Z-score with epsilon guard for zero std to prevent division by zero.
    
    Args:
        series: Price series
        n: Window size
        epsilon: Small value to replace zero std (default 1e-6)
        precision: Decimal places for rounding (default 6)
        
    Returns:
        Rounded z-score series
    """
    mu = sma(series, n, precision)
    sd = rolling_std(series, n, precision)
    # Prevent division by zero
    sd_safe = sd.replace(0.0, epsilon)
    z = (series - mu) / sd_safe
    return z.round(precision)

def above(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Boolean helper: a > b aligned to index."""
    return (series_a > series_b).astype(bool)

def below(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    return (series_a < series_b).astype(bool)


# ============================================================================
# Additional Technical Indicators for Dashboard
# ============================================================================

def rsi(close: pd.Series, n: int = 14, precision: int = PRECISION) -> pd.Series:
    """
    Relative Strength Index (RSI).

    Args:
        close: Close price series
        n: RSI period (default 14)
        precision: Decimal places for rounding

    Returns:
        RSI values between 0 and 100
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing (EMA with alpha=1/n)
    avg_gain = gain.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False).mean()

    # Prevent division by zero
    avg_loss_safe = avg_loss.replace(0.0, EPSILON)
    rs = avg_gain / avg_loss_safe

    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.round(precision)


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    precision: int = PRECISION
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence (MACD).

    Args:
        close: Close price series
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
        precision: Decimal places for rounding

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = (ema_fast - ema_slow).round(precision)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().round(precision)
    histogram = (macd_line - signal_line).round(precision)

    return macd_line, signal_line, histogram


def bollinger_bands(
    close: pd.Series,
    n: int = 20,
    num_std: float = 2.0,
    precision: int = PRECISION
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.

    Args:
        close: Close price series
        n: Period for moving average (default 20)
        num_std: Number of standard deviations (default 2)
        precision: Decimal places for rounding

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle = sma(close, n, precision)
    std = rolling_std(close, n, precision)

    upper = (middle + num_std * std).round(precision)
    lower = (middle - num_std * std).round(precision)

    return upper, middle, lower


def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    precision: int = PRECISION
) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP).

    Note: This is cumulative VWAP (resets daily in practice).
    For intraday use, ensure data is for a single session.

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        volume: Volume series
        precision: Decimal places for rounding

    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    tp_volume = typical_price * volume

    cumulative_tp_vol = tp_volume.cumsum()
    cumulative_vol = volume.cumsum()

    # Prevent division by zero
    cumulative_vol_safe = cumulative_vol.replace(0, EPSILON)

    vwap_val = cumulative_tp_vol / cumulative_vol_safe
    return vwap_val.round(precision)


def compute_all_indicators(df: pd.DataFrame) -> dict:
    """
    Compute all technical indicators for a DataFrame with OHLCV data.

    Args:
        df: DataFrame with columns [open, high, low, close, volume]

    Returns:
        Dictionary with latest values of all indicators
    """
    if df.empty or len(df) < 30:
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Compute indicators
    rsi_val = rsi(close, 14)
    macd_line, macd_signal, macd_hist = macd(close, 12, 26, 9)
    bb_upper, bb_middle, bb_lower = bollinger_bands(close, 20, 2.0)
    atr_val = atr(high, low, close, 14)
    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50) if len(df) >= 50 else pd.Series([None] * len(df))
    sma_200 = sma(close, 200) if len(df) >= 200 else pd.Series([None] * len(df))

    # Get latest values
    return {
        "rsi": float(rsi_val.iloc[-1]) if not pd.isna(rsi_val.iloc[-1]) else None,
        "macd": float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None,
        "macd_signal": float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None,
        "macd_histogram": float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else None,
        "bb_upper": float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None,
        "bb_middle": float(bb_middle.iloc[-1]) if not pd.isna(bb_middle.iloc[-1]) else None,
        "bb_lower": float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None,
        "atr": float(atr_val.iloc[-1]) if not pd.isna(atr_val.iloc[-1]) else None,
        "sma_20": float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None,
        "sma_50": float(sma_50.iloc[-1]) if len(df) >= 50 and not pd.isna(sma_50.iloc[-1]) else None,
        "sma_200": float(sma_200.iloc[-1]) if len(df) >= 200 and not pd.isna(sma_200.iloc[-1]) else None,
    }
