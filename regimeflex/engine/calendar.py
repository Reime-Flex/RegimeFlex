from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable, Tuple, List
import datetime as _dt

def _parse_iso_dates(iso_list: Iterable[str]) -> List[date]:
    out: List[date] = []
    for s in iso_list or []:
        try:
            out.append(_dt.date.fromisoformat(str(s)))
        except Exception:
            # ignore bad lines silently; you can harden later
            pass
    return out

def is_third_friday(d: date) -> bool:
    """Monthly OPEX: 3rd Friday of the month."""
    # Find first day of month and its weekday
    first = d.replace(day=1)
    # 0=Mon ... 4=Fri ... 6=Sun
    first_friday_offset = (4 - first.weekday()) % 7
    third_friday = first + timedelta(days=first_friday_offset + 14)  # +2 weeks from first Friday
    return d == third_friday

def is_opex(d: date, overrides: Iterable[str] | None = None) -> bool:
    """True if third Friday OR in overrides list."""
    if is_third_friday(d):
        return True
    ov = _parse_iso_dates(overrides or [])
    return d in ov

def is_fomc_blackout(
    d: date,
    fomc_meetings: Iterable[str] | None = None,
    window: Tuple[int, int] = (-1, 1)
) -> bool:
    """
    True if within [meeting+window[0], meeting+window[1]] for any meeting date.
    Example window (-1, +1) means: day before, meeting day, day after.
    """
    meets = _parse_iso_dates(fomc_meetings or [])
    lo, hi = window
    for m in meets:
        if m + timedelta(days=lo) <= d <= m + timedelta(days=hi):
            return True
    return False
