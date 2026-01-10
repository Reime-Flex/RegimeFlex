"""
Manual Kill Switch
==================
High-friction kill switch that monitors data/state/kill_switch.json.
If "active": true, all trade logic must return "FLAT" immediately.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .identity import RegimeFlexIdentity as RF


KILL_SWITCH_FILE = Path("data/state/kill_switch.json")


def is_kill_switch_active() -> Optional[Dict[str, Any]]:
    """
    Check if manual kill switch is active.
    
    Returns:
        Dict with kill switch state if active, None if inactive or file doesn't exist
        {
            "active": bool,
            "reason": str,
            "activated_at": str (ISO timestamp),
            "activated_by": str
        }
    """
    if not KILL_SWITCH_FILE.exists():
        return None
    
    try:
        data = json.loads(KILL_SWITCH_FILE.read_text())
        if bool(data.get("active", False)):
            return data
        return None
    except (json.JSONDecodeError, KeyError) as e:
        RF.print_log(f"Error reading kill switch file: {e}", "ERROR")
        return None
    except Exception as e:
        RF.print_log(f"Unexpected error reading kill switch: {e}", "ERROR")
        return None


def activate_kill_switch(reason: str = "Manual activation", activated_by: str = "manual") -> bool:
    """
    Activate kill switch immediately.
    
    Args:
        reason: Reason for activation
        activated_by: Who/what activated it (e.g., "manual", "api", "script")
        
    Returns:
        True if activated successfully
    """
    KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    state = {
        "active": True,
        "reason": reason,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by
    }
    
    try:
        KILL_SWITCH_FILE.write_text(json.dumps(state, indent=2))
        RF.print_log(f"⛔ KILL SWITCH ACTIVATED: {reason}", "ERROR")
        return True
    except Exception as e:
        RF.print_log(f"Failed to activate kill switch: {e}", "ERROR")
        return False


def deactivate_kill_switch() -> bool:
    """
    Deactivate kill switch.
    
    Returns:
        True if deactivated successfully
    """
    try:
        if KILL_SWITCH_FILE.exists():
            KILL_SWITCH_FILE.unlink()
            RF.print_log("✅ Kill switch deactivated", "SUCCESS")
            return True
        else:
            RF.print_log("Kill switch file does not exist", "INFO")
            return False
    except Exception as e:
        RF.print_log(f"Failed to deactivate kill switch: {e}", "ERROR")
        return False


def get_kill_switch_status() -> Dict[str, Any]:
    """
    Get current kill switch status.
    
    Returns:
        Dict with status information
    """
    active_state = is_kill_switch_active()
    
    if active_state:
        return {
            "active": True,
            "reason": active_state.get("reason", "Unknown"),
            "activated_at": active_state.get("activated_at", "Unknown"),
            "activated_by": active_state.get("activated_by", "Unknown")
        }
    else:
        return {
            "active": False,
            "reason": None,
            "activated_at": None,
            "activated_by": None
        }

