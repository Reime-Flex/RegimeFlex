"""
System Health Monitor
=====================
Comprehensive system health check for heartbeat telemetry.
Monitors CPU, memory, disk, and API connectivity.
"""
from __future__ import annotations

import json
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.config import Config


def check_system_health() -> Dict[str, Any]:
    """
    Comprehensive system health check.
    
    Returns:
        Dict with health metrics:
        {
            "timestamp": ISO timestamp,
            "cpu_percent": float,
            "memory_percent": float,
            "disk_percent": float,
            "api_health": {
                "polygon": bool,
                "alpaca": bool
            }
        }
    """
    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "api_health": {}
    }
    
    # System resource monitoring (if psutil available)
    if PSUTIL_AVAILABLE:
        try:
            health["cpu_percent"] = psutil.cpu_percent(interval=1)
            health["memory_percent"] = psutil.virtual_memory().percent
            health["disk_percent"] = psutil.disk_usage("/").percent
        except Exception as e:
            RF.print_log(f"System resource check failed: {e}", "RISK")
    else:
        RF.print_log("psutil not available, skipping system resource checks", "INFO")
    
    # API health checks
    from regimeflex.config.paths import PROJECT_ROOT
    data_cfg = Config(PROJECT_ROOT)._load_yaml("config/data.yaml") if (Config(PROJECT_ROOT).root / "config/data.yaml").exists() else {}
    
    # Check Polygon API
    polygon_healthy = False
    try:
        poly_cfg = data_cfg.get("polygon", {}) or {}
        base_url = poly_cfg.get("base_url", "")
        if base_url:
            # Simple connectivity check (lightweight endpoint)
            test_url = base_url.replace("{symbol}", "QQQ").replace("{_symbol}", "QQQ")
            test_url = test_url.split("?")[0]  # Remove query params
            # Use a minimal test - just check if endpoint responds
            r = requests.get(
                "https://api.polygon.io/v2/aggs/ticker/QQQ/range/1/day/2024-01-01/2024-01-02",
                params={"apiKey": "test"},
                timeout=5
            )
            # 401 is expected without valid key, but means API is up
            polygon_healthy = r.status_code < 500
    except Exception as e:
        RF.print_log(f"Polygon API health check failed: {e}", "RISK")
        polygon_healthy = False
    
    health["api_health"]["polygon"] = polygon_healthy
    
    # Check Alpaca API
    alpaca_healthy = False
    try:
        # Check Alpaca clock endpoint (public, no auth required)
        r = requests.get("https://paper-api.alpaca.markets/v2/clock", timeout=5)
        alpaca_healthy = r.status_code < 500
    except Exception as e:
        RF.print_log(f"Alpaca API health check failed: {e}", "RISK")
        alpaca_healthy = False
    
    health["api_health"]["alpaca"] = alpaca_healthy
    
    return health


def format_health_summary(health: Dict[str, Any]) -> str:
    """
    Format health check results as human-readable string.
    
    Args:
        health: Health dict from check_system_health()
        
    Returns:
        Formatted string summary
    """
    parts = []
    
    if health.get("cpu_percent") is not None:
        parts.append(f"CPU: {health['cpu_percent']:.1f}%")
    
    if health.get("memory_percent") is not None:
        parts.append(f"Mem: {health['memory_percent']:.1f}%")
    
    if health.get("disk_percent") is not None:
        parts.append(f"Disk: {health['disk_percent']:.1f}%")
    
    api_health = health.get("api_health", {})
    api_parts = []
    if api_health.get("polygon"):
        api_parts.append("Polygon✅")
    else:
        api_parts.append("Polygon❌")
    
    if api_health.get("alpaca"):
        api_parts.append("Alpaca✅")
    else:
        api_parts.append("Alpaca❌")
    
    if api_parts:
        parts.append(" | ".join(api_parts))
    
    return " | ".join(parts) if parts else "Health check unavailable"

