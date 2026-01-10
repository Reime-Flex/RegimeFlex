from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import json

def log_volatility_decay(
    lev_symbol: str, 
    lev_df: pd.DataFrame, 
    idx_symbol: str, 
    idx_df: pd.DataFrame, 
    lookback: int = 20, 
    leverage: float = 3.0,
    save_daily: bool = True,
    log_dir: str = "logs/decay"
) -> Dict[str, Any]:
    """
    Institutional-Grade Entry: Leverage Decay Logger
    
    Calculate and log 'Volatility Decay' on TQQQ/SQQQ holdings daily, comparing
    our performance against the raw QQQ index to ensure the 'Swing' strategy is
    actually outperforming.
    
    Decay = (Leveraged Return) - (Leverage * Index Return)
    
    This tracks whether the 3x leveraged ETF strategy is generating alpha or
    being eroded by volatility decay.
    
    Args:
        lev_symbol: Leveraged ETF symbol (TQQQ, SQQQ, PSQ)
        lev_df: Leveraged ETF price DataFrame
        idx_symbol: Index symbol (QQQ)
        idx_df: Index price DataFrame
        lookback: Days to look back for calculation (default 20)
        leverage: Leverage factor (default 3.0 for TQQQ/SQQQ)
        save_daily: Whether to save daily decay log (default True)
        log_dir: Directory for daily logs (default "logs/decay")
        
    Returns:
        Dict with decay statistics and performance comparison
    """
    if lev_df is None or idx_df is None or lev_df.empty or idx_df.empty:
        return {"note": "missing_data"}
        
    # Align dates
    # Assuming 'close' column exists
    # Calculate daily returns
    lev_ret = lev_df["close"].pct_change().dropna()
    idx_ret = idx_df["close"].pct_change().dropna()
    
    # Align
    common_idx = lev_ret.index.intersection(idx_ret.index)
    lev_ret = lev_ret.loc[common_idx]
    idx_ret = idx_ret.loc[common_idx]
    
    if len(common_idx) == 0:
        return {"note": "no_common_dates"}
        
    # Determine effective leverage
    eff_lev = leverage
    if "SQQQ" in lev_symbol.upper() or "SPXU" in lev_symbol.upper():
         eff_lev = -leverage
    elif "PSQ" in lev_symbol.upper():
         eff_lev = -1.0
    
    # Filter to lookback
    if len(common_idx) > lookback:
        start_date = common_idx[-lookback]
        recent_lev = lev_ret.loc[start_date:]
        recent_idx = idx_ret.loc[start_date:]
    else:
        recent_lev = lev_ret
        recent_idx = idx_ret

    # Daily diff: How much did the ETF deviate from Perfect Leverage * Index?
    daily_tracking_diff = recent_lev - (eff_lev * recent_idx)
    
    # Calculate stats
    avg_decay_bps = daily_tracking_diff.mean() * 10000
    std_decay_bps = daily_tracking_diff.std() * 10000
    
    # Cumulative Decay: Compare Actual Growth vs Theoretical Growth
    # Theoretical = Product(1 + lev * r_idx)
    # Actual = Product(1 + r_etf)
    actual_growth = (1 + recent_lev).prod()
    theoretical_growth = (1 + (eff_lev * recent_idx)).prod()
    
    decay_pct = (actual_growth - theoretical_growth) * 100
    
    # Performance comparison: Are we outperforming?
    # Positive decay_pct = underperformance (decay eating returns)
    # Negative decay_pct = outperformance (strategy edge working)
    outperforming = decay_pct < 0
    
    # Calculate today's decay (if we have today's data)
    today_decay_bps = None
    if len(daily_tracking_diff) > 0:
        today_decay_bps = round(daily_tracking_diff.iloc[-1] * 10000, 2)
    
    result = {
        "symbol": lev_symbol,
        "index": idx_symbol,
        "lookback_days": len(recent_lev),
        "leverage": eff_lev,
        "daily_tracking_error_bps": round(avg_decay_bps, 2),
        "daily_tracking_error_std_bps": round(std_decay_bps, 2),
        "today_decay_bps": today_decay_bps,
        "period_decay_pct": round(decay_pct, 2),
        "theoretical_growth": round((theoretical_growth-1)*100, 2),
        "actual_growth": round((actual_growth-1)*100, 2),
        "outperforming": outperforming,
        "edge_working": outperforming,  # Alias for clarity
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Save daily log if enabled
    if save_daily:
        try:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Save today's entry
            today = datetime.now(timezone.utc).date().isoformat()
            daily_file = log_path / f"{lev_symbol}_decay_{today}.json"
            
            # Load existing or create new
            if daily_file.exists():
                with open(daily_file, "r") as f:
                    daily_data = json.load(f)
            else:
                daily_data = {"symbol": lev_symbol, "index": idx_symbol, "entries": []}
            
            # Append today's entry
            daily_data["entries"].append(result)
            
            # Keep only last 30 days
            daily_data["entries"] = daily_data["entries"][-30:]
            
            # Save
            with open(daily_file, "w") as f:
                json.dump(daily_data, f, indent=2)
                
        except Exception as e:
            # Don't fail if logging fails
            result["log_error"] = str(e)
    
    return result
