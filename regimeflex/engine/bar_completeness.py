"""
Bar Completeness Checker
=========================
Prevents look-ahead bias by verifying bar completeness before using prices.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

import pandas as pd

from .identity import RegimeFlexIdentity as RF


def is_bar_complete(bar_date: pd.Timestamp | datetime, current_time: datetime | None = None) -> bool:
    """
    Check if a bar date represents a complete (closed) bar.
    
    A bar is considered complete if its date is before today's date.
    This prevents using today's incomplete bar for signal generation.
    
    Args:
        bar_date: The date/timestamp of the bar to check
        current_time: Current time for comparison (defaults to now UTC)
        
    Returns:
        True if bar is complete (can be used safely), False if incomplete
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Normalize bar_date to date
    if hasattr(bar_date, 'date'):
        if hasattr(bar_date, 'tz'):
            # Timezone-aware timestamp
            bar_date_obj = bar_date.date()
        else:
            # Naive timestamp
            bar_date_obj = bar_date.date()
    elif isinstance(bar_date, datetime):
        bar_date_obj = bar_date.date()
    else:
        # Assume it's already a date
        bar_date_obj = bar_date
    
    # Normalize current_time to date
    if isinstance(current_time, datetime):
        current_date = current_time.date()
    else:
        current_date = current_time
    
    # Bar is complete if its date is before today
    is_complete = bar_date_obj < current_date
    
    if not is_complete:
        RF.print_log(
            f"⚠️ Incomplete bar detected: {bar_date_obj} >= {current_date} (today)",
            "RISK"
        )
    
    return is_complete


def get_safe_price(
    df: pd.DataFrame,
    use_t1_if_incomplete: bool = True,
    fallback_to_last: bool = False
) -> Tuple[float, bool, str]:
    """
    Get a safe price from DataFrame, ensuring no look-ahead bias.
    
    Args:
        df: DataFrame with datetime index and 'close' column
        use_t1_if_incomplete: If True, use T-1 bar if last bar is incomplete
        fallback_to_last: If True, fall back to last bar if T-1 unavailable
        
    Returns:
        Tuple of (price, is_safe, reason)
        - price: Safe price to use (float)
        - is_safe: True if price is from complete bar
        - reason: Human-readable reason for the price choice
    """
    if df is None or df.empty:
        return 0.0, False, "Empty DataFrame"
    
    if len(df) == 0:
        return 0.0, False, "No data available"
    
    last_bar_date = df.index[-1]
    last_price = float(df["close"].iloc[-1])
    
    # Check if last bar is complete
    if is_bar_complete(last_bar_date):
        return last_price, True, f"Using last bar price ${last_price:.2f} (complete)"
    
    # Last bar is incomplete - use T-1 if available
    if use_t1_if_incomplete and len(df) > 1:
        t1_price = float(df["close"].iloc[-2])
        t1_date = df.index[-2]
        
        if is_bar_complete(t1_date):
            RF.print_log(
                f"Using T-1 price ${t1_price:.2f} (last bar incomplete, date={last_bar_date})",
                "RISK"
            )
            return t1_price, True, f"Using T-1 price ${t1_price:.2f} (last bar incomplete)"
        else:
            # T-1 is also incomplete (shouldn't happen, but handle gracefully)
            if fallback_to_last:
                RF.print_log(
                    f"⚠️ T-1 also incomplete, falling back to last bar ${last_price:.2f}",
                    "RISK"
                )
                return last_price, False, f"Fallback to incomplete bar ${last_price:.2f}"
            else:
                return 0.0, False, "Both last and T-1 bars incomplete"
    else:
        # No T-1 available or use_t1_if_incomplete=False
        if fallback_to_last:
            RF.print_log(
                f"⚠️ Using incomplete bar ${last_price:.2f} (no T-1 available)",
                "RISK"
            )
            return last_price, False, f"Using incomplete bar ${last_price:.2f}"
        else:
            return 0.0, False, "Last bar incomplete and T-1 unavailable"

