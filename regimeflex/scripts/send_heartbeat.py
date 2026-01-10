#!/usr/bin/env python3
"""
Guardian Heartbeat Sender
=========================
Sends scheduled heartbeat messages to Discord/Telegram.
Designed to run via PM2 cron (every 4 hours).

Usage:
    python regimeflex/scripts/send_heartbeat.py
    
    # Force send immediately (for testing):
    python regimeflex/scripts/send_heartbeat.py --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.env import load_env
from regimeflex.engine.config import Config
from regimeflex.engine.guardian.alerting import AlertManager
from regimeflex.engine.guardian.watchdog import Watchdog


def get_current_status(root: Path) -> dict:
    """
    Get current system status for heartbeat message.
    
    Returns:
        Dictionary with regime, equity, and other status info
    """
    status = {
        "regime": "UNKNOWN",
        "equity": 0.0,
        "last_cycle": None,
        "additional_info": {}
    }
    
    # Try to get last heartbeat data from watchdog
    try:
        watchdog = Watchdog(root)
        heartbeat = watchdog.get_last_heartbeat()
        
        if heartbeat:
            if heartbeat.last_regime:
                status["regime"] = heartbeat.last_regime
            if heartbeat.last_equity:
                status["equity"] = heartbeat.last_equity
            status["last_cycle"] = heartbeat.timestamp
            status["additional_info"]["cycle_count"] = heartbeat.cycle_count
    except Exception as e:
        RF.print_log(f"Failed to get watchdog status: {e}", "WARNING")
    
    # Try to get live equity from broker
    try:
        from regimeflex.engine.exec_alpaca import get_alpaca_client_creds
        import requests
        
        creds = get_alpaca_client_creds()
        if creds.key and creds.secret:
            url = creds.base_url.rstrip("/") + "/v2/account"
            headers = {
                "APCA-API-KEY-ID": creds.key,
                "APCA-API-SECRET-KEY": creds.secret,
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                account = r.json()
                status["equity"] = float(account.get("equity", 0))
                status["additional_info"]["buying_power"] = f"${float(account.get('buying_power', 0)):,.0f}"
    except Exception as e:
        RF.print_log(f"Failed to get broker equity: {e}", "WARNING")
    
    # Try to get regime from most recent report
    try:
        reports_dir = root / "reports"
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("daily_report_*.html"), reverse=True)
            if reports:
                # Parse regime from report filename or content
                status["additional_info"]["latest_report"] = reports[0].name
    except Exception:
        pass
    
    return status


def main():
    """Send heartbeat message."""
    parser = argparse.ArgumentParser(description="Send Guardian heartbeat")
    parser.add_argument("--force", action="store_true", help="Force send immediately")
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parent.parent
    
    RF.print_log("=" * 50, "INFO")
    RF.print_log("Guardian Heartbeat Sender", "SUCCESS")
    RF.print_log("=" * 50, "INFO")
    
    # Load environment
    try:
        load_env(root)
    except Exception as e:
        RF.print_log(f"Failed to load environment: {e}", "WARNING")
    
    # Get current status
    status = get_current_status(root)
    RF.print_log(f"Current status: {status}", "INFO")
    
    # Send heartbeat
    try:
        alert_manager = AlertManager(root)
        
        success = alert_manager.send_heartbeat(
            regime=status["regime"],
            equity=status["equity"],
            last_cycle=status["last_cycle"],
            additional_info=status["additional_info"]
        )
        
        if success:
            RF.print_log("Heartbeat sent successfully", "SUCCESS")
        else:
            RF.print_log("Heartbeat send failed", "ERROR")
            sys.exit(1)
            
    except Exception as e:
        RF.print_log(f"Failed to send heartbeat: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
