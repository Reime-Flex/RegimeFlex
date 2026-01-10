#!/usr/bin/env python3
"""
Guardian Watchdog Monitor
=========================
Standalone process that monitors the main trading loop health.
Designed to run as a separate PM2 process.

If the trading loop hasn't completed a cycle in the configured timeout,
this monitor will trigger a restart via PM2.

Usage:
    python regimeflex/scripts/watchdog_monitor.py
    
    # Or via PM2:
    pm2 start ecosystem.config.js
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.guardian.watchdog import Watchdog


def main():
    """Run the watchdog monitor loop."""
    root = Path(__file__).resolve().parent.parent
    watchdog = Watchdog(root)
    
    RF.print_log("=" * 50, "INFO")
    RF.print_log("Guardian Watchdog Monitor Started", "SUCCESS")
    RF.print_log(f"Timeout: {watchdog.config.timeout_minutes} minutes", "INFO")
    RF.print_log(f"Check interval: {watchdog.config.check_interval_sec} seconds", "INFO")
    RF.print_log(f"Action on stale: {watchdog.config.action_on_stale}", "INFO")
    RF.print_log("=" * 50, "INFO")
    
    if not watchdog.config.enabled:
        RF.print_log("Watchdog is disabled in config. Exiting.", "WARNING")
        return
    
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    while True:
        try:
            status = watchdog.get_health_status()
            
            if status["healthy"]:
                age = status.get("heartbeat_age_minutes")
                if age is not None:
                    RF.print_log(
                        f"Health check OK: heartbeat {age:.1f}m old (limit: {watchdog.config.timeout_minutes}m)",
                        "SUCCESS"
                    )
                else:
                    RF.print_log("Health check OK: waiting for first heartbeat", "INFO")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                age = status.get("heartbeat_age_minutes")
                
                RF.print_log(
                    f"Health check FAILED: heartbeat stale ({age:.1f}m > {watchdog.config.timeout_minutes}m)",
                    "ERROR"
                )
                
                if consecutive_failures >= max_consecutive_failures:
                    RF.print_log(
                        f"Triggering recovery after {consecutive_failures} consecutive failures",
                        "ERROR"
                    )
                    watchdog.trigger_recovery()
                    consecutive_failures = 0
                    
                    # Wait extra time after triggering recovery
                    time.sleep(60)
                else:
                    RF.print_log(
                        f"Stale detection {consecutive_failures}/{max_consecutive_failures}",
                        "WARNING"
                    )
            
        except KeyboardInterrupt:
            RF.print_log("Watchdog monitor stopped by user", "INFO")
            break
        except Exception as e:
            RF.print_log(f"Watchdog monitor error: {e}", "ERROR")
        
        time.sleep(watchdog.config.check_interval_sec)


if __name__ == "__main__":
    main()
