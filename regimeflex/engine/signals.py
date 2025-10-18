from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

from .indicators import sma, rolling_std, zscore, realized_vol_pct_change

@dataclass(frozen=True)
class RegimeState:
    bull: bool                 # QQQ above slow MA?
    vix: float | None = None   # pass in if available
    qqq_rvol_20: float | None = None  # annualized realized vol (0.25 = 25%)

@dataclass(frozen=True)
class TrendSignal:
    entry: bool
    exit: bool
    reason: str

@dataclass(frozen=True)
class MRSignal:
    direction: str    # "LONG", "SHORT", or "FLAT"
    entry: bool
    exit: bool
    z: float | None
    reason: str

# ---------- Regime detection ----------

def detect_regime(qqq_close: pd.Series, slow: int = 200) -> RegimeState:
    slow_ma = sma(qqq_close, slow)
    bull = bool((qqq_close.iloc[-1] > slow_ma.iloc[-1]) if pd.notna(slow_ma.iloc[-1]) else False)
    # caller can also compute rvol + provide VIX
    rvol20 = realized_vol_pct_change(qqq_close, 20).iloc[-1] if qqq_close.size else None
    return RegimeState(bull=bull, vix=None, qqq_rvol_20=float(rvol20) if pd.notna(rvol20) else None)

# ---------- Trend engine (refined) ----------

def trend_signal(qqq: pd.DataFrame, regime: RegimeState,
                 vix_max: float = 30.0, qqq_vol_50d_max: float = 0.40) -> TrendSignal:
    close = qqq["close"]
    s5, s20, s50, s100, s200 = sma(close, 5), sma(close, 20), sma(close, 50), sma(close, 100), sma(close, 200)

    # Entry: Close > SMA(200) AND SMA(20) > SMA(50) AND SMA(5) > SMA(20)
    entry_cond = (
        pd.notna(s200.iloc[-1]) and
        close.iloc[-1] > s200.iloc[-1] and
        s20.iloc[-1] > s50.iloc[-1] and
        s5.iloc[-1]  > s20.iloc[-1]
    )

    # Exit: Close < SMA(100) OR SMA(20) < SMA(50)
    exit_cond = (
        (pd.notna(s100.iloc[-1]) and close.iloc[-1] < s100.iloc[-1]) or
        (pd.notna(s20.iloc[-1]) and pd.notna(s50.iloc[-1]) and s20.iloc[-1] < s50.iloc[-1])
    )

    # Regime filter: VIX < 30 AND 50d vol < 40%
    # We approximate 50d vol with realized_vol over 50 days (annualized)
    rvol50 = realized_vol_pct_change(close, 50).iloc[-1]
    vix_ok = (regime.vix is None) or (regime.vix < vix_max)
    vol_ok = (pd.notna(rvol50) and float(rvol50) < qqq_vol_50d_max)

    if not vix_ok:
        return TrendSignal(entry=False, exit=False, reason="VIX block")
    if not vol_ok:
        return TrendSignal(entry=False, exit=False, reason="High 50d realized vol block")

    return TrendSignal(entry=bool(entry_cond), exit=bool(exit_cond),
                       reason="entry/exit evaluated under regime filter OK")

# ---------- Mean-Reversion engine (regime-adaptive z-score) ----------

def mr_signal(df: pd.DataFrame, regime: RegimeState,
              z_len: int = 20, vol_confirm_mult: float = 1.2,
              time_stop_days_bull: int = 5, time_stop_days_bear: int = 3) -> MRSignal:
    """
    Uses (close - SMA(20)) / rolling_std(20) with volume confirmation.
    Holding-day stop is enforced by the caller in live loop;
    here we only compute entry/exit conditions at 'now'.
    """
    close = df["close"]
    vol = df["volume"]
    mu = sma(close, z_len)
    sd = rolling_std(close, z_len)
    z = float(((close.iloc[-1] - mu.iloc[-1]) / sd.iloc[-1])) if (pd.notna(mu.iloc[-1]) and pd.notna(sd.iloc[-1]) and sd.iloc[-1] != 0) else None

    # Volume confirmation: volume > 1.2 × SMA(volume, 20)
    vavg = sma(vol, 20).iloc[-1] if vol.size else None
    vol_conf = (vol.iloc[-1] > vol_confirm_mult * vavg) if (vavg is not None and pd.notna(vavg)) else True

    if z is None:
        return MRSignal(direction="FLAT", entry=False, exit=False, z=None, reason="Insufficient data")

    if regime.bull:
        entry = (z < -2.0) and vol_conf
        exit = (z > 0.0)
        direction = "LONG" if entry else ("FLAT" if not exit else "FLAT")
        reason = "Bull regime: buy dips (z<-2), exit when z>0"
    else:
        entry = (z > 2.0) and vol_conf
        exit = (z < 0.0)
        direction = "SHORT" if entry else ("FLAT" if not exit else "FLAT")
        reason = "Bear regime: short bounces (z>2), exit when z<0"

    return MRSignal(direction=direction, entry=bool(entry), exit=bool(exit), z=z, reason=reason)
