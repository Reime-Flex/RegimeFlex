"""
Guardian Watchdog Module
=========================
Monitors the trading loop health and triggers recovery when stale.

Features:
- Heartbeat file touch after each cycle
- Staleness detection
- PM2 restart signaling
- Health status reporting
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..identity import RegimeFlexIdentity as RF
from ..config import Config
from .system_health import check_system_health, format_health_summary


@dataclass
class WatchdogConfig:
    """Watchdog configuration."""
    enabled: bool = True
    timeout_minutes: int = 10
    heartbeat_file: str = ".guardian_heartbeat"
    action_on_stale: str = "restart"  # restart | alert_only
    check_interval_sec: int = 60


@dataclass
class HeartbeatData:
    """Data stored in the heartbeat file."""
    timestamp: datetime
    pid: int
    cycle_count: int
    last_regime: Optional[str]
    last_equity: Optional[float]
    extra: Dict[str, Any]


class Watchdog:
    """
    Trading loop health monitor.
    
    The main trading loop calls `touch()` at the end of each successful cycle.
    A separate watchdog process monitors the heartbeat file age and triggers
    recovery if too stale.
    
    Usage (in trading loop):
        watchdog = Watchdog()
        
        while True:
            run_trading_cycle()
            watchdog.touch(regime="BULL", equity=50000.0)
    
    Usage (in watchdog monitor):
        watchdog = Watchdog()
        
        while True:
            if not watchdog.check_health():
                watchdog.trigger_recovery()
            time.sleep(60)
    """
    
    def __init__(self, root: Path | str = "."):
        self.root = Path(root) if isinstance(root, str) else root
        self.config = self._load_config()
        self._heartbeat_path = self.root / self.config.heartbeat_file
        self._cycle_count = 0
        self._alert_manager = None  # Lazy load
    
    def _load_config(self) -> WatchdogConfig:
        """Load watchdog configuration from guardian.yaml."""
        try:
            cfg = Config(self.root)
            guardian = cfg._load_yaml("config/guardian.yaml") or {}
            wd_cfg = guardian.get("watchdog", {})
            
            return WatchdogConfig(
                enabled=wd_cfg.get("enabled", True),
                timeout_minutes=wd_cfg.get("timeout_minutes", 10),
                heartbeat_file=wd_cfg.get("heartbeat_file", ".guardian_heartbeat"),
                action_on_stale=wd_cfg.get("action_on_stale", "restart"),
                check_interval_sec=wd_cfg.get("check_interval_sec", 60)
            )
        except Exception as e:
            RF.print_log(f"Failed to load watchdog config: {e}", "WARNING")
            return WatchdogConfig()
    
    def _get_alert_manager(self):
        """Lazy load alert manager."""
        if self._alert_manager is None:
            from .alerting import get_alert_manager
            self._alert_manager = get_alert_manager(self.root)
        return self._alert_manager
    
    def touch(
        self,
        regime: Optional[str] = None,
        equity: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Touch the heartbeat file to signal healthy cycle completion.
        
        Call this at the end of each successful trading cycle.
        
        Args:
            regime: Current market regime
            equity: Current account equity
            extra: Additional data to store
        """
        if not self.config.enabled:
            return
        
        self._cycle_count += 1
        
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "cycle_count": self._cycle_count,
            "last_regime": regime,
            "last_equity": equity,
            "extra": extra or {}
        }
        
        try:
            self._heartbeat_path.write_text(json.dumps(data, indent=2))
            RF.print_log(f"Watchdog heartbeat: cycle {self._cycle_count}", "SUCCESS")
        except Exception as e:
            RF.print_log(f"Failed to write watchdog heartbeat: {e}", "ERROR")
    
    def get_last_heartbeat(self) -> Optional[HeartbeatData]:
        """
        Read the last heartbeat data.
        
        Returns:
            HeartbeatData if heartbeat file exists and is valid, None otherwise
        """
        if not self._heartbeat_path.exists():
            return None
        
        try:
            data = json.loads(self._heartbeat_path.read_text())
            return HeartbeatData(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                pid=data.get("pid", 0),
                cycle_count=data.get("cycle_count", 0),
                last_regime=data.get("last_regime"),
                last_equity=data.get("last_equity"),
                extra=data.get("extra", {})
            )
        except Exception as e:
            RF.print_log(f"Failed to read heartbeat: {e}", "WARNING")
            return None
    
    def get_heartbeat_age_minutes(self) -> Optional[float]:
        """
        Get the age of the last heartbeat in minutes.
        
        Returns:
            Age in minutes, or None if no heartbeat exists
        """
        heartbeat = self.get_last_heartbeat()
        if heartbeat is None:
            return None
        
        now = datetime.now(timezone.utc)
        age = (now - heartbeat.timestamp).total_seconds() / 60
        return age
    
    def is_stale(self) -> bool:
        """
        Check if the heartbeat is stale (older than timeout).
        
        Returns:
            True if heartbeat is missing or older than timeout_minutes
        """
        age = self.get_heartbeat_age_minutes()
        
        if age is None:
            # No heartbeat file - consider stale if watchdog is enabled
            return self.config.enabled
        
        return age > self.config.timeout_minutes
    
    def check_health(self) -> bool:
        """
        Check if the trading loop is healthy.
        
        Returns:
            True if healthy (heartbeat is fresh), False if stale
        """
        if not self.config.enabled:
            return True
        
        return not self.is_stale()
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Dictionary with health status details
        """
        heartbeat = self.get_last_heartbeat()
        age = self.get_heartbeat_age_minutes()
        is_healthy = self.check_health()
        
        status = {
            "healthy": is_healthy,
            "enabled": self.config.enabled,
            "timeout_minutes": self.config.timeout_minutes,
            "heartbeat_age_minutes": round(age, 2) if age else None,
            "heartbeat_exists": heartbeat is not None
        }
        
        if heartbeat:
            status.update({
                "last_heartbeat": heartbeat.timestamp.isoformat(),
                "pid": heartbeat.pid,
                "cycle_count": heartbeat.cycle_count,
                "last_regime": heartbeat.last_regime,
                "last_equity": heartbeat.last_equity
            })
        
        return status
    
    def trigger_recovery(self) -> bool:
        """
        Trigger recovery action based on configuration.
        
        Returns:
            True if recovery action was taken
        """
        age = self.get_heartbeat_age_minutes()
        RF.print_log(
            f"Watchdog: heartbeat stale ({age:.1f}m > {self.config.timeout_minutes}m)",
            "ERROR"
        )
        
        # Send alert
        try:
            alert_mgr = self._get_alert_manager()
            heartbeat = self.get_last_heartbeat()
            
            alert_mgr.send_emergency(
                error_type="WATCHDOG_STALE",
                error_message=f"Trading loop has not completed a cycle in {age:.1f} minutes",
                trace=f"Last heartbeat: {heartbeat.timestamp if heartbeat else 'never'}\n"
                      f"Last PID: {heartbeat.pid if heartbeat else 'unknown'}\n"
                      f"Cycles completed: {heartbeat.cycle_count if heartbeat else 0}",
                service="trading_loop"
            )
        except Exception as e:
            RF.print_log(f"Failed to send watchdog alert: {e}", "ERROR")
        
        # Take action
        if self.config.action_on_stale == "restart":
            return self._trigger_pm2_restart()
        else:
            RF.print_log("Watchdog: alert_only mode, not restarting", "WARNING")
            return True
    
    def _trigger_pm2_restart(self) -> bool:
        """
        Trigger PM2 to restart the main process.
        
        Returns:
            True if restart was triggered
        """
        try:
            # First try PM2 restart
            result = subprocess.run(
                ["pm2", "restart", "regimeflex"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                RF.print_log("Watchdog: PM2 restart triggered", "SUCCESS")
                return True
            else:
                RF.print_log(f"PM2 restart failed: {result.stderr}", "ERROR")
                
        except FileNotFoundError:
            RF.print_log("PM2 not found, attempting direct process kill", "WARNING")
        except subprocess.TimeoutExpired:
            RF.print_log("PM2 restart timed out", "ERROR")
        except Exception as e:
            RF.print_log(f"PM2 restart error: {e}", "ERROR")
        
        # Fallback: try to kill the stale process
        return self._kill_stale_process()
    
    def _kill_stale_process(self) -> bool:
        """
        Kill the stale trading process.
        
        Returns:
            True if kill was attempted
        """
        heartbeat = self.get_last_heartbeat()
        if not heartbeat or not heartbeat.pid:
            RF.print_log("No PID in heartbeat, cannot kill", "WARNING")
            return False
        
        try:
            os.kill(heartbeat.pid, signal.SIGTERM)
            RF.print_log(f"Sent SIGTERM to PID {heartbeat.pid}", "WARNING")
            return True
        except ProcessLookupError:
            RF.print_log(f"PID {heartbeat.pid} no longer exists", "WARNING")
            return True
        except PermissionError:
            RF.print_log(f"Permission denied to kill PID {heartbeat.pid}", "ERROR")
            return False
        except Exception as e:
            RF.print_log(f"Failed to kill process: {e}", "ERROR")
            return False
    
    def clear_heartbeat(self) -> None:
        """Remove the heartbeat file (for testing)."""
        if self._heartbeat_path.exists():
            self._heartbeat_path.unlink()
            RF.print_log("Heartbeat file cleared", "INFO")


# Singleton for convenience
_default_watchdog: Optional[Watchdog] = None


def get_watchdog(root: Path | str = ".") -> Watchdog:
    """Get or create the default Watchdog instance."""
    global _default_watchdog
    if _default_watchdog is None:
        _default_watchdog = Watchdog(root)
    return _default_watchdog


def touch_heartbeat(
    regime: Optional[str] = None,
    equity: Optional[float] = None,
    root: Path | str = "."
) -> None:
    """Convenience function to touch the watchdog heartbeat."""
    get_watchdog(root).touch(regime=regime, equity=equity)
