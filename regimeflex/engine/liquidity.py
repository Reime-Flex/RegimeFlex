# engine/liquidity.py
from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List

def dollar_vol(df: pd.DataFrame) -> pd.Series:
    """Assumes columns: 'close', 'volume'."""
    return (df["close"].astype(float) * df["volume"].astype(float))

def rolling_adv(df: pd.DataFrame, window: int) -> float:
    dv = dollar_vol(df)
    if len(dv) == 0:
        return 0.0
    return float(dv.rolling(window, min_periods=1).mean().iloc[-1])

def badge(frac: float, warn: float, crit: float) -> str:
    if frac >= crit: return "RED"
    if frac >= warn: return "AMBER"
    return "GREEN"

def assess_depth(intents: List[Dict[str, Any]],
                 adv_map: Dict[str, float],
                 warn_frac: float,
                 crit_frac: float) -> Dict[str, Any]:
    """
    intents: [{'symbol': 'QQQ', 'qty': 100, 'side': 'BUY', 'price': 430.12, ...}, ...]
    Returns summary + per-intent annotations.
    """
    out_rows = []
    red = amber = 0
    for it in intents or []:
        sym = str(it.get("symbol","")).upper()
        qty = float(it.get("qty", 0.0))
        px  = float(it.get("price", 0.0))  # your planner's reference/limit
        notional = abs(qty * px)
        adv = float(adv_map.get(sym, 0.0))
        frac = (notional / adv) if adv > 0 else 0.0
        b = badge(frac, warn_frac, crit_frac)
        if b == "RED": red += 1
        elif b == "AMBER": amber += 1
        out_rows.append({
            "symbol": sym,
            "qty": qty,
            "price": px,
            "notional": round(notional, 2),
            "adv": round(adv, 2),
            "of_adv": round(frac, 4),   # fraction of ADV
            "badge": b
        })
    return {
        "rows": out_rows,
        "counts": {"RED": red, "AMBER": amber, "GREEN": max(0, len(out_rows) - red - amber)}
    }


def check_zscore_liquidity(
    symbol: str, 
    current_vol: float, 
    history_df: pd.DataFrame, 
    window: int = 20, 
    z_thresh: float = -2.0,
    delay_minutes: int = 30
) -> Dict[str, Any]:
    """
    Institutional-Grade Entry: Liquidity Check
    
    Before entering a position, check the 'Average Daily Volume' (ADV).
    If the current volume is 2 standard deviations below the mean, delay the entry
    by 30 minutes to wait for better liquidity.
    
    This prevents entering positions during low-volume periods that can cause
    excessive slippage in 3x leveraged ETFs.
    
    Args:
        symbol: Trading symbol
        current_vol: Current volume (from latest bar)
        history_df: Historical price/volume DataFrame
        window: Rolling window for ADV calculation (default 20 days)
        z_thresh: Z-score threshold (default -2.0 = 2 SD below mean)
        delay_minutes: Minutes to delay entry if liquidity is low (default 30)
        
    Returns:
        Dict with:
        - blocked: bool - Whether to block/delay entry
        - reason: str - Reason for blocking
        - z_score: float - Calculated Z-score
        - mean: float - Mean volume
        - current: float - Current volume
        - delay_minutes: int - Minutes to delay (if blocked)
        - retry_after: str - ISO timestamp when to retry (if blocked)
    """
    if history_df is None or history_df.empty: 
        return {"blocked": False, "reason": "No history"}
    
    # Calculate rolling stats on VOLUME
    # Assumes history_df index is sorted.
    # We use .shift(1) effectively to ensure the mean/std are derived from PRIOR days, 
    # not influenced by the potentially partial current day if it's in the DF.
    
    v = history_df["volume"].astype(float)
    if len(v) < window:
         return {"blocked": False, "reason": "Insufficient history for Z-score"}

    # Rolling stats (mean/std of PREVIOUS 'window' days)
    # .shift(1) moves T-1 to T position.
    prior_mean_s = v.rolling(window).mean().shift(1)
    prior_std_s  = v.rolling(window).std().shift(1)
    
    mean = prior_mean_s.iloc[-1]
    std  = prior_std_s.iloc[-1]
    
    if pd.isna(mean) or pd.isna(std) or std == 0:
        return {"blocked": False, "reason": "Invalid volatility stats"}

    z_score = (current_vol - mean) / std
    
    if z_score < z_thresh:
        # Current volume is 2+ SD below mean - delay entry by 30 minutes
        from datetime import datetime, timezone, timedelta
        retry_after = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        
        return {
            "blocked": True,
            "reason": f"Low Liquidity ({symbol}): Vol Z-Score {z_score:.2f} < {z_thresh} (2 SD below mean). Delaying entry by {delay_minutes} minutes.",
            "z_score": round(z_score, 3),
            "mean": round(mean, 0),
            "std": round(std, 0),
            "current": current_vol,
            "delay_minutes": delay_minutes,
            "retry_after": retry_after.isoformat(),
            "adv": round(mean, 0),  # Average Daily Volume
            "current_vs_adv_pct": round((current_vol / mean * 100) if mean > 0 else 0, 2)
        }
        
    return {
        "blocked": False, 
        "z_score": round(z_score, 3),
        "mean": round(mean, 0),
        "std": round(std, 0),
        "current": current_vol,
        "adv": round(mean, 0)
    }

