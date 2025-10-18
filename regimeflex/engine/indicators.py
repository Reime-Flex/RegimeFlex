from __future__ import annotations
import pandas as pd
import numpy as np

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).mean()

def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    # Wilder's smoothing
    return tr.ewm(alpha=1/n, adjust=False).mean()

def rolling_std(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(window=n, min_periods=n).std(ddof=0)

def realized_vol_pct_change(series: pd.Series, n: int = 20, annualization: int = 252) -> pd.Series:
    """Annualized realized volatility of daily returns (as a fraction, not %)."""
    rets = series.pct_change()
    vol = rets.rolling(n, min_periods=n).std(ddof=0) * np.sqrt(annualization)
    return vol

def zscore(series: pd.Series, n: int = 20) -> pd.Series:
    mu = sma(series, n)
    sd = rolling_std(series, n)
    z = (series - mu) / sd
    return z

def above(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Boolean helper: a > b aligned to index."""
    return (series_a > series_b).astype(bool)

def below(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    return (series_a < series_b).astype(bool)
