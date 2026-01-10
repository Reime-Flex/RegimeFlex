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
