# engine/timing.py
from __future__ import annotations
from typing import Tuple
from .config import Config

def eod_ready(minutes_to_close: int) -> Tuple[bool, str]:
    """
    Returns (ready?, reason). Uses config/schedule.yaml → eod_guard.
    ready = True if minutes_to_close <= min_minutes_before_close OR override is enabled.
    """
    cfg = Config(".")._load_yaml("config/schedule.yaml") if (Config(".").root / "config/schedule.yaml").exists() else {}
    guard = (cfg.get("eod_guard") or {})
    window = int(guard.get("min_minutes_before_close", 30))
    override = bool(guard.get("allow_early_override", False))

    if override:
        return True, f"override=true (window={window}m)"

    if minutes_to_close <= window:
        return True, f"within window ({minutes_to_close}m ≤ {window}m)"

    return False, f"too early ({minutes_to_close}m > {window}m)"
