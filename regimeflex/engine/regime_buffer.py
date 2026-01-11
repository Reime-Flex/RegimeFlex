from __future__ import annotations
from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime, timezone

from regimeflex.config.paths import REGIME_STATE_FILE

def load_regime_state() -> Dict[str, Any]:
    """Load persistent regime state with last confirmed regime."""
    if not REGIME_STATE_FILE.exists():
        return {"confirmed_regime": None, "since_date": None, "consecutive_days": 0}
    try:
        return json.loads(REGIME_STATE_FILE.read_text())
    except Exception:
        return {"confirmed_regime": None, "since_date": None, "consecutive_days": 0}

def save_regime_state(state: Dict[str, Any]) -> None:
    REGIME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGIME_STATE_FILE.write_text(json.dumps(state, indent=2))

def detect_regime_with_hysteresis(
    qqq_close: float,
    slow_ma: float,
    current_regime_state: Dict[str, Any],
    buffer_pct: float = 0.02,  # 2% buffer band
    confirmation_days: int = 2  # Require 2 days above/below to flip
) -> tuple[bool, str, Dict[str, Any]]:
    """
    Regime detection with hysteresis to prevent "flashing" signals.
    
    Returns: (is_bull, reason, updated_state)
    """
    if slow_ma <= 0:
        return False, "Invalid SMA", current_regime_state
    
    upper_band = slow_ma * (1 + buffer_pct)
    lower_band = slow_ma * (1 - buffer_pct)
    
    last_confirmed = current_regime_state.get("confirmed_regime")
    consecutive = current_regime_state.get("consecutive_days", 0)
    
    # Determine raw signal
    if qqq_close > upper_band:
        raw_signal = True
        position = "ABOVE_UPPER"
    elif qqq_close < lower_band:
        raw_signal = False
        position = "BELOW_LOWER"
    else:
        # Within buffer zone - maintain current regime
        raw_signal = last_confirmed if last_confirmed is not None else True
        position = "IN_BUFFER"
    
    # Apply confirmation logic
    if last_confirmed is None:
        # First run: accept raw signal
        new_state = {
            "confirmed_regime": raw_signal,
            "since_date": datetime.now(timezone.utc).isoformat(),
            "consecutive_days": 1
        }
        return raw_signal, f"Initial regime set: {position}", new_state
    
    if raw_signal == last_confirmed:
        # Regime confirmed, reset counter
        new_state = {
            "confirmed_regime": last_confirmed,
            "since_date": current_regime_state.get("since_date"),
            "consecutive_days": 0
        }
        return last_confirmed, f"Regime confirmed: {position}", new_state
    
    # Signal differs from confirmed regime
    if position == "IN_BUFFER":
        # Don't count buffer zone days toward flip
        return last_confirmed, f"In buffer zone, maintaining {last_confirmed}", current_regime_state
    
    # Outside buffer and different from confirmed
    consecutive += 1
    if consecutive >= confirmation_days:
        # Flip confirmed
        new_state = {
            "confirmed_regime": raw_signal,
            "since_date": datetime.now(timezone.utc).isoformat(),
            "consecutive_days": 0
        }
        return raw_signal, f"Regime FLIP after {confirmation_days} days: {position}", new_state
    else:
        # Not enough days yet
        new_state = {
            "confirmed_regime": last_confirmed,
            "since_date": current_regime_state.get("since_date"),
            "consecutive_days": consecutive
        }
        return last_confirmed, f"Pending flip ({consecutive}/{confirmation_days}): {position}", new_state
