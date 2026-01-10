#!/usr/bin/env python3
"""
Guardian Status Dashboard
=========================
Display the status of all Guardian components:
- Circuit breaker states
- Watchdog health
- Alerting configuration
- Recent alerts

Usage:
    python regimeflex/scripts/guardian_status.py
    python regimeflex/scripts/guardian_status.py --test-alert  # Send test alert
    python regimeflex/scripts/guardian_status.py --json        # Output as JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.env import load_env
from regimeflex.engine.config import Config
from regimeflex.engine.guardian.alerting import AlertManager, AlertLevel
from regimeflex.engine.guardian.circuit_breaker import CircuitBreaker
from regimeflex.engine.guardian.watchdog import Watchdog


def print_header(title: str) -> None:
    """Print a formatted header."""
    RF.print_log("", "INFO")
    RF.print_log("=" * 50, "INFO")
    RF.print_log(f"  {title}", "INFO")
    RF.print_log("=" * 50, "INFO")


def print_row(label: str, value: str, status: str = "INFO") -> None:
    """Print a formatted row."""
    RF.print_log(f"  {label:<25} {value}", status)


def get_full_status(root: Path) -> dict:
    """Get comprehensive Guardian status."""
    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guardian": {},
        "watchdog": {},
        "circuit_breakers": {},
        "alerting": {}
    }
    
    # Guardian config
    try:
        cfg = Config(root)
        guardian_cfg = cfg._load_yaml("config/guardian.yaml") or {}
        status["guardian"]["enabled"] = guardian_cfg.get("enabled", True)
        status["guardian"]["config_loaded"] = True
    except Exception as e:
        status["guardian"]["enabled"] = False
        status["guardian"]["config_loaded"] = False
        status["guardian"]["error"] = str(e)
    
    # Watchdog status
    try:
        watchdog = Watchdog(root)
        status["watchdog"] = watchdog.get_health_status()
    except Exception as e:
        status["watchdog"]["error"] = str(e)
    
    # Circuit breaker states
    try:
        status["circuit_breakers"] = CircuitBreaker.get_all_states()
        if not status["circuit_breakers"]:
            status["circuit_breakers"]["_note"] = "No circuit breakers registered yet"
    except Exception as e:
        status["circuit_breakers"]["error"] = str(e)
    
    # Alerting configuration
    try:
        alert_mgr = AlertManager(root)
        status["alerting"] = {
            "telegram_enabled": alert_mgr._config.telegram_enabled,
            "discord_enabled": alert_mgr._config.discord_enabled,
            "uptime_hours": round(alert_mgr.get_uptime_hours(), 2),
            "last_heartbeat": alert_mgr.get_last_heartbeat().isoformat() if alert_mgr.get_last_heartbeat() else None
        }
    except Exception as e:
        status["alerting"]["error"] = str(e)
    
    return status


def display_status(status: dict) -> None:
    """Display status in human-readable format."""
    print_header("GUARDIAN MODULE STATUS")
    
    # Guardian config
    guardian = status.get("guardian", {})
    config_status = "SUCCESS" if guardian.get("config_loaded") else "ERROR"
    enabled_status = "SUCCESS" if guardian.get("enabled") else "WARNING"
    print_row("Config Loaded", str(guardian.get("config_loaded", False)), config_status)
    print_row("Enabled", str(guardian.get("enabled", False)), enabled_status)
    
    # Watchdog
    print_header("WATCHDOG")
    watchdog = status.get("watchdog", {})
    
    if "error" in watchdog:
        print_row("Status", f"Error: {watchdog['error']}", "ERROR")
    else:
        health_status = "SUCCESS" if watchdog.get("healthy") else "ERROR"
        print_row("Healthy", str(watchdog.get("healthy", False)), health_status)
        print_row("Enabled", str(watchdog.get("enabled", False)), "INFO")
        print_row("Timeout", f"{watchdog.get('timeout_minutes', 0)} minutes", "INFO")
        
        age = watchdog.get("heartbeat_age_minutes")
        if age is not None:
            age_status = "SUCCESS" if age < watchdog.get("timeout_minutes", 10) else "ERROR"
            print_row("Heartbeat Age", f"{age:.1f} minutes", age_status)
        else:
            print_row("Heartbeat Age", "No heartbeat yet", "WARNING")
        
        if watchdog.get("last_regime"):
            print_row("Last Regime", watchdog["last_regime"], "INFO")
        if watchdog.get("last_equity"):
            print_row("Last Equity", f"${watchdog['last_equity']:,.2f}", "INFO")
        if watchdog.get("cycle_count"):
            print_row("Cycle Count", str(watchdog["cycle_count"]), "INFO")
    
    # Circuit Breakers
    print_header("CIRCUIT BREAKERS")
    breakers = status.get("circuit_breakers", {})
    
    if "_note" in breakers:
        print_row("Status", breakers["_note"], "INFO")
    elif "error" in breakers:
        print_row("Status", f"Error: {breakers['error']}", "ERROR")
    else:
        for name, state in breakers.items():
            if name.startswith("_"):
                continue
            
            cb_state = state.get("state", "unknown")
            failures = state.get("failure_count", 0)
            max_failures = state.get("max_failures", 3)
            
            if cb_state == "closed":
                cb_status = "SUCCESS"
            elif cb_state == "half_open":
                cb_status = "WARNING"
            else:
                cb_status = "ERROR"
            
            print_row(f"[{name}]", f"{cb_state.upper()} ({failures}/{max_failures} failures)", cb_status)
            
            if state.get("last_error"):
                print_row("  Last Error", state["last_error"][:50] + "...", "ERROR")
    
    # Alerting
    print_header("ALERTING")
    alerting = status.get("alerting", {})
    
    if "error" in alerting:
        print_row("Status", f"Error: {alerting['error']}", "ERROR")
    else:
        tg_status = "SUCCESS" if alerting.get("telegram_enabled") else "WARNING"
        dc_status = "SUCCESS" if alerting.get("discord_enabled") else "WARNING"
        
        print_row("Telegram", "Enabled" if alerting.get("telegram_enabled") else "Disabled", tg_status)
        print_row("Discord", "Enabled" if alerting.get("discord_enabled") else "Disabled", dc_status)
        print_row("Uptime", f"{alerting.get('uptime_hours', 0):.1f} hours", "INFO")
        
        if alerting.get("last_heartbeat"):
            print_row("Last Heartbeat", alerting["last_heartbeat"], "INFO")
    
    RF.print_log("", "INFO")
    RF.print_log("=" * 50, "INFO")


def test_alert(root: Path) -> bool:
    """Send a test alert to all channels."""
    RF.print_log("Sending test alert...", "INFO")
    
    try:
        alert_mgr = AlertManager(root)
        
        success = alert_mgr.send(
            "🧪 *Test Alert*\n\n"
            "This is a test message from the Guardian module.\n"
            "If you received this, alerting is working correctly.\n\n"
            f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            AlertLevel.INFO
        )
        
        if success:
            RF.print_log("Test alert sent successfully!", "SUCCESS")
        else:
            RF.print_log("Test alert failed to send", "ERROR")
        
        return success
        
    except Exception as e:
        RF.print_log(f"Test alert error: {e}", "ERROR")
        return False


def main():
    """Run the Guardian status dashboard."""
    parser = argparse.ArgumentParser(description="Guardian status dashboard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--test-alert", action="store_true", help="Send a test alert")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    
    # Load environment
    try:
        load_env(root)
    except Exception:
        pass
    
    if args.test_alert:
        success = test_alert(root)
        sys.exit(0 if success else 1)
    
    status = get_full_status(root)
    
    if args.json:
        print(json.dumps(status, indent=2, default=str))
    else:
        display_status(status)


if __name__ == "__main__":
    main()
