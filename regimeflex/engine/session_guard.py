# engine/session_guard.py
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone, date
from typing import Tuple

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def is_full_holiday(d: date, root: Path = Path(".")) -> bool:
    cfg = _load_json(root / "config" / "us_holidays.json")
    days = set((cfg.get("full_holidays") or []))
    return d.isoformat() in days

def is_half_day(d: date, root: Path = Path(".")) -> bool:
    cfg = _load_json(root / "config" / "us_halfdays.json")
    days = set((cfg.get("half_days") or []))
    return d.isoformat() in days

def session_status(today_utc: datetime | None = None, root: Path = Path(".")) -> Tuple[str, str]:
    """
    Returns (status, note) where status ∈ {"FULL", "NO_SESSION", "HALF_DAY"}.
    Purely local-file driven. If no files or no match → assume FULL.
    """
    if today_utc is None:
        today_utc = datetime.now(timezone.utc)
    d = today_utc.date()
    if is_full_holiday(d, root):
        return "NO_SESSION", "full_holiday"
    if is_half_day(d, root):
        return "HALF_DAY", "early_close"
    return "FULL", "ok"

