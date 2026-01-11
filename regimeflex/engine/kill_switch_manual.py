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

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.config.paths import KILL_SWITCH_FILE
from regimeflex.utils.atomic_file import atomic_write_json, atomic_read_json, atomic_delete_file


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
    
    # Use atomic read to prevent reading corrupted files
    data = atomic_read_json(KILL_SWITCH_FILE, default=None)
    if data and bool(data.get("active", False)):
        return data
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
    state = {
        "active": True,
        "reason": reason,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by
    }
    
    # Use atomic write to prevent corruption
    success = atomic_write_json(KILL_SWITCH_FILE, state, indent=2)
    if success:
        RF.print_log(f"⛔ KILL SWITCH ACTIVATED: {reason}", "ERROR")
        return True
    else:
        RF.print_log(f"Failed to activate kill switch: write failed", "ERROR")
        return False


def deactivate_kill_switch() -> bool:
    """
    Deactivate kill switch.
    
    Returns:
        True if deactivated successfully
    """
    # Use atomic delete to safely remove file
    success = atomic_delete_file(KILL_SWITCH_FILE)
    if success:
        RF.print_log("✅ Kill switch deactivated", "SUCCESS")
        return True
    else:
        if not KILL_SWITCH_FILE.exists():
            RF.print_log("Kill switch file does not exist", "INFO")
            return False
        else:
            RF.print_log("Failed to deactivate kill switch: delete failed", "ERROR")
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

