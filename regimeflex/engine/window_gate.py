# engine/window_gate.py
from __future__ import annotations
from datetime import datetime, time, timezone
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


def _parse_hhmm(s: str) -> time:
    """Parse HH:MM string into time object."""
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def window_gate_check(schedule_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if current time is within the allowed execution window.

    Returns:
      {
        "allowed": bool,
        "reason": str | None,
        "now": str,
        "tz": str,
        "window": {"start": "...", "end": "..."} | None,
      }
    """
    wg = (schedule_cfg.get("window_gate") or {})
    if not wg.get("enabled", False):
        return {"allowed": True, "reason": None, "now": None, "tz": None, "window": None}

    tz_name = wg.get("timezone", "America/New_York")
    
    # Handle zoneinfo availability
    if ZoneInfo is None:
        # Fallback: use UTC if zoneinfo not available
        tz = None
        now = datetime.now(timezone.utc)
        tz_name = "UTC"
    else:
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        except Exception:
            # If timezone is invalid, fallback to UTC
            tz = None
            now = datetime.now(timezone.utc)
            tz_name = "UTC"
    
    now_t = now.time()

    # Check weekend blocking
    if wg.get("block_weekends", True):
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return {
                "allowed": False,
                "reason": "Weekend blocked by window gate",
                "now": now.isoformat(),
                "tz": tz_name,
                "window": {"start": wg.get("start"), "end": wg.get("end")},
            }

    # Check time window
    start_str = wg.get("start")
    end_str = wg.get("end")
    
    if not start_str or not end_str:
        # If window not configured, allow (but log warning)
        return {
            "allowed": True,
            "reason": "Window gate enabled but start/end not configured",
            "now": now.isoformat(),
            "tz": tz_name,
            "window": None,
        }

    try:
        start = _parse_hhmm(start_str)
        end = _parse_hhmm(end_str)
    except Exception:
        # If parsing fails, allow (but log warning)
        return {
            "allowed": True,
            "reason": "Window gate enabled but start/end format invalid",
            "now": now.isoformat(),
            "tz": tz_name,
            "window": {"start": start_str, "end": end_str},
        }

    # Check if current time is within window
    # Handle case where window spans midnight (e.g., 23:00 to 01:00)
    if start <= end:
        # Normal case: window within same day
        allowed = (start <= now_t <= end)
    else:
        # Window spans midnight: check if before end OR after start
        allowed = (now_t >= start) or (now_t <= end)

    if not allowed:
        return {
            "allowed": False,
            "reason": "Outside allowed execution window",
            "now": now.isoformat(),
            "tz": tz_name,
            "window": {"start": start_str, "end": end_str},
        }

    return {
        "allowed": True,
        "reason": None,
        "now": now.isoformat(),
        "tz": tz_name,
        "window": {"start": start_str, "end": end_str},
    }


def morning_rush_check(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if current time is within Morning Rush (9:30 - 9:45 AM EST).
    
    Institutional-Grade Entry: Prevents trades in first 15 minutes of market open
    to avoid 'Opening Gap' volatility common in 3x leveraged ETFs.
    
    Ref: 'The Morning Rush Filter'
    """
    # Get config or use defaults
    mr_cfg = cfg.get("morning_rush", {}) or {}
    
    if not mr_cfg.get("enabled", True):
        return {"blocked": False, "reason": "Morning Rush disabled"}
    
    # Defaults
    tz_name = mr_cfg.get("timezone", "America/New_York")
    start_str = mr_cfg.get("start", "09:30")
    end_str = mr_cfg.get("end", "09:45")
    
    # Handle zoneinfo availability
    if ZoneInfo is None:
        tz = None
        now = datetime.now(timezone.utc)
        tz_name = "UTC" # Fallback, though rush hour logic relies on EST
    else:
        try:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        except Exception:
            tz = None
            now = datetime.now(timezone.utc)
            tz_name = "UTC"

    now_t = now.time()
    
    try:
        start = _parse_hhmm(start_str)
        end = _parse_hhmm(end_str)
    except Exception:
        return {"blocked": False, "reason": "Morning Rush parse error"}

    # Check range
    if start <= now_t < end:
        minutes_remaining = ((end.hour * 60 + end.minute) - (now_t.hour * 60 + now_t.minute))
        return {
            "blocked": True,
            "reason": f"Morning Rush Filter active ({start_str}-{end_str} {tz_name})",
            "now": now_t.isoformat(),
            "tz": tz_name,
            "minutes_remaining": minutes_remaining,
            "window_start": start_str,
            "window_end": end_str
        }

    return {"blocked": False, "reason": None}

