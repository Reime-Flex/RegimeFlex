# engine/regime_accuracy.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _ann_realized_vol(close: pd.Series, n: int) -> pd.Series:
    rets = close.pct_change()
    vol = rets.rolling(n, min_periods=n).std()
    return vol * np.sqrt(252.0)


def build_proxy_labels(df: pd.DataFrame, vol_win: int, high_vol_thr: float) -> pd.Series:
    """
    df must have 'close'. Returns proxy_bull: True/False per row.
    """
    c = df["close"]
    sma20 = _sma(c, 20)
    sma50 = _sma(c, 50)
    sma200 = _sma(c, 200)
    trend_bull = (sma20 > sma50) & (c > sma200)
    ann_vol = _ann_realized_vol(c, vol_win)
    low_vol = (ann_vol <= high_vol_thr)
    proxy_bull = (trend_bull & low_vol).fillna(False)
    return proxy_bull


def shift_for_lookahead(series: pd.Series, lookahead_days: int) -> pd.Series:
    """
    Align proxy at t to score label at t-lookahead_days.
    """
    return series.shift(-lookahead_days)


def accuracy_score(y_true: pd.Series, y_pred: pd.Series) -> Tuple[float, Dict[str, int]]:
    """
    Boolean series aligned on index. Returns (accuracy, confusion_counts).
    """
    mask = y_true.notna() & y_pred.notna()
    yt = y_true[mask].astype(bool)
    yp = y_pred[mask].astype(bool)
    if yt.empty:
        return float("nan"), {"TP": 0, "TN": 0, "FP": 0, "FN": 0, "N": 0}
    TP = int(((yt == True) & (yp == True)).sum())   # noqa: E712
    TN = int(((yt == False) & (yp == False)).sum()) # noqa: E712
    FP = int(((yt == False) & (yp == True)).sum())  # noqa: E712
    FN = int(((yt == True) & (yp == False)).sum())  # noqa: E712
    acc = (TP + TN) / float(TP + TN + FP + FN)
    return float(acc), {"TP": TP, "TN": TN, "FP": FP, "FN": FN, "N": TP + TN + FP + FN}

