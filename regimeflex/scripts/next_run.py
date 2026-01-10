#!/usr/bin/env python
from __future__ import annotations

from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, Any
import sys

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.config import Config
from engine.window_gate import window_gate_check, _parse_hhmm
from engine.market_day_gate import market_day_check

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None

try:
    import pandas_market_calendars as mcal
except ImportError:
    mcal = None


def is_market_day(day: str, md_cfg: Dict[str, Any]) -> bool:
    """Check if a given day is a market trading day."""
    if mcal is None:
        # If library not available, assume it's a trading day
        return True
    
    try:
        cal_name = md_cfg.get("calendar", "NYSE")
        cal = mcal.get_calendar(cal_name)
        sched = cal.schedule(start_date=day, end_date=day)
        return not sched.empty
    except Exception:
        # If check fails, assume it's a trading day
        return True


def main() -> int:
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        root = cwd / "regimeflex"
    else:
        root = cwd
    
    cfg = Config(root)
    schedule_cfg = cfg._load_yaml("config/schedule.yaml") if (cfg.root / "config/schedule.yaml").exists() else {}

    wg = (schedule_cfg.get("window_gate") or {})
    md_cfg = (schedule_cfg.get("market_day_gate") or {})

    tz_name = wg.get("timezone", "America/New_York")
    
    # Handle zoneinfo availability
    if ZoneInfo is None:
        print("Warning: zoneinfo not available, using UTC")
        tz = None
        now = datetime.now()
        tz_name = "UTC"
    else:
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        except Exception:
            print(f"Warning: timezone {tz_name} invalid, using UTC")
            tz = None
            now = datetime.now()
            tz_name = "UTC"

    # Current status
    window = window_gate_check(schedule_cfg)
    md = {"allowed": True, "reason": None}
    if md_cfg.get("enabled", False):
        md = market_day_check(md_cfg)

    print("RegimeFlex Next Run Preview")
    print("------------------------------------------------------------")
    print(f"Now ({tz_name}): {now.isoformat()}")
    print(f"Window gate allowed: {window.get('allowed')}  reason: {window.get('reason') or 'N/A'}")
    if md_cfg.get("enabled", False):
        print(f"Market day allowed: {md.get('allowed')}  reason: {md.get('reason') or 'N/A'}")
    else:
        print("Market day allowed: True (market_day_gate disabled)")

    # Compute next window start
    if not wg.get("enabled", False):
        print("")
        print("Window gate disabled - no next run time calculated")
        print("------------------------------------------------------------")
        return 0

    start_str = wg.get("start", "15:50")
    end_str = wg.get("end", "16:00")
    
    try:
        start_t = _parse_hhmm(start_str)
        end_t = _parse_hhmm(end_str)
    except Exception:
        print("")
        print(f"Error: Invalid window time format (start: {start_str}, end: {end_str})")
        print("------------------------------------------------------------")
        return 1

    # Find next eligible day (today if still ahead, else next trading day)
    if tz is None:
        # If no timezone, use naive datetime
        day_cursor = now.date()
        tz_for_date = None
    else:
        day_cursor = now.date()
        tz_for_date = tz

    for _ in range(15):  # cap search to avoid infinite loops
        day_iso = day_cursor.isoformat()

        # Weekend block
        if wg.get("block_weekends", True):
            if tz_for_date:
                weekday_check = datetime(day_cursor.year, day_cursor.month, day_cursor.day, tzinfo=tz_for_date).weekday()
            else:
                weekday_check = datetime(day_cursor.year, day_cursor.month, day_cursor.day).weekday()
            if weekday_check >= 5:  # Saturday = 5, Sunday = 6
                day_cursor = day_cursor + timedelta(days=1)
                continue

        # Market day block
        if md_cfg.get("enabled", False):
            if not is_market_day(day_iso, md_cfg):
                day_cursor = day_cursor + timedelta(days=1)
                continue

        # Candidate start datetime
        if tz_for_date:
            candidate = datetime(
                day_cursor.year, day_cursor.month, day_cursor.day,
                start_t.hour, start_t.minute, tzinfo=tz_for_date
            )
        else:
            candidate = datetime(
                day_cursor.year, day_cursor.month, day_cursor.day,
                start_t.hour, start_t.minute
            )

        # If today, and we are already past the end time, move to next day
        today_same = (day_cursor == now.date())
        if today_same:
            if tz_for_date:
                end_dt = datetime(
                    day_cursor.year, day_cursor.month, day_cursor.day,
                    end_t.hour, end_t.minute, tzinfo=tz_for_date
                )
            else:
                end_dt = datetime(
                    day_cursor.year, day_cursor.month, day_cursor.day,
                    end_t.hour, end_t.minute
                )
            if now > end_dt:
                day_cursor = day_cursor + timedelta(days=1)
                continue

        # If today and we're before start, candidate is today start.
        # If today and inside window, candidate is now.
        if today_same and (start_t <= now.time() <= end_t):
            candidate = now

        print("")
        print(f"Next eligible run time ({tz_name}): {candidate.isoformat()}")
        print(f"Window: {start_str} → {end_str}")
        print("------------------------------------------------------------")
        return 0

    print("")
    print("Next eligible run time: not found in search horizon (15 days)")
    print("------------------------------------------------------------")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

