#!/usr/bin/env python
"""
Manual Kill Switch Control
===========================
Activate or deactivate the manual kill switch for RegimeFlex.

Usage:
    python scripts/kill_switch.py activate "Reason for kill"
    python scripts/kill_switch.py deactivate
    python scripts/kill_switch.py status
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from regimeflex.engine.kill_switch_manual import (
    activate_kill_switch,
    deactivate_kill_switch,
    get_kill_switch_status
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/kill_switch.py [activate|deactivate|status] [reason]")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "activate":
        reason = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Manual activation"
        if activate_kill_switch(reason=reason, activated_by="script"):
            print(f"✅ Kill switch activated: {reason}")
            return 0
        else:
            print("❌ Failed to activate kill switch")
            return 1
    
    elif command == "deactivate":
        if deactivate_kill_switch():
            print("✅ Kill switch deactivated")
            return 0
        else:
            print("⚠️ Kill switch was not active")
            return 0
    
    elif command == "status":
        status = get_kill_switch_status()
        if status["active"]:
            print(f"⛔ KILL SWITCH ACTIVE")
            print(f"   Reason: {status['reason']}")
            print(f"   Activated at: {status['activated_at']}")
            print(f"   Activated by: {status['activated_by']}")
            return 1
        else:
            print("✅ Kill switch inactive")
            return 0
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python scripts/kill_switch.py [activate|deactivate|status] [reason]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
