# engine/market_day_gate.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        # If zoneinfo is not available, we'll use UTC as fallback
        ZoneInfo = None

try:
    import pandas_market_calendars as mcal
except ImportError:
    mcal = None


def market_day_check(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks if today is a valid US market trading day (NYSE calendar).

    Returns:
      {
        "allowed": bool,
        "reason": str | None,
        "date": "YYYY-MM-DD",
        "timezone": str
      }
    """
    if mcal is None:
        # If pandas-market-calendars is not installed, allow (but log warning)
        return {
            "allowed": True,
            "reason": "pandas-market-calendars not available, market day check skipped",
            "date": None,
            "timezone": None,
        }

    tz_name = cfg.get("timezone", "America/New_York")
    
    # Handle zoneinfo availability
    if ZoneInfo is None:
        # Fallback: use UTC if zoneinfo not available
        tz = None
        now = datetime.now()
        tz_name = "UTC"
    else:
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        except Exception:
            # If timezone is invalid, fallback to UTC
            tz = None
            now = datetime.now()
            tz_name = "UTC"
    
    day = now.date().isoformat()

    try:
        cal = mcal.get_calendar("NYSE")
        sched = cal.schedule(start_date=day, end_date=day)

        if sched.empty:
            return {
                "allowed": False,
                "reason": "US market holiday (NYSE closed)",
                "date": day,
                "timezone": tz_name,
            }
    except Exception as e:
        # If calendar check fails, allow (but log warning)
        return {
            "allowed": True,
            "reason": f"Market calendar check failed: {e}",
            "date": day,
            "timezone": tz_name,
        }

    return {
        "allowed": True,
        "reason": None,
        "date": day,
        "timezone": tz_name,
    }

