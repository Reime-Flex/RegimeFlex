"""
Centralized path definitions for RegimeFlex.

This module provides absolute paths calculated relative to the project root,
ensuring paths work correctly regardless of the current working directory
(e.g., when PM2 changes CWD).

All paths are absolute and directories are created automatically on import.

Usage:
    from regimeflex.config.paths import PROJECT_ROOT, STATE_DIR, RUN_LOCK_FILE
    
    # Use constants instead of string literals
    lock_file = RUN_LOCK_FILE  # Instead of Path("data/state/run.lock")
"""

from pathlib import Path
from typing import Optional

# Calculate project root (3 levels up from this file)
# This file is at: regimeflex/config/paths.py
# Project root is: regimeflex/config/paths.py -> .. -> .. -> .. = project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Directory paths (absolute)
DATA_DIR = PROJECT_ROOT / 'data'
STATE_DIR = DATA_DIR / 'state'
CONFIG_DIR = PROJECT_ROOT / 'regimeflex' / 'config'
LOGS_DIR = PROJECT_ROOT / 'logs'
REPORTS_DIR = PROJECT_ROOT / 'reports'
REPLAYS_DIR = PROJECT_ROOT / 'replays'
CACHE_DIR = DATA_DIR / 'cache'

# Subdirectories
LOGS_TRADING_DIR = LOGS_DIR / 'trading'
LOGS_AUDIT_DIR = LOGS_DIR / 'audit'
REPORTS_MONTHLY_DIR = REPORTS_DIR / 'monthly'

# State file paths (HIGH PRIORITY - critical for operation)
RUN_LOCK_FILE = STATE_DIR / 'run.lock'
POSITIONS_FILE = STATE_DIR / 'positions.json'
KILL_SWITCH_FILE = STATE_DIR / 'kill_switch.json'
REGIME_STATE_FILE = STATE_DIR / 'regime_state.json'
ORDER_WAL_FILE = STATE_DIR / 'order_wal.jsonl'
TRADING_STATE_FILE = STATE_DIR / 'trading_state.json'

# Guardian files
GUARDIAN_HEARTBEAT_FILE = PROJECT_ROOT / '.guardian_heartbeat'

# Config file paths (MEDIUM PRIORITY)
RISK_CONFIG = CONFIG_DIR / 'risk.yaml'
EXPOSURE_CONFIG = CONFIG_DIR / 'exposure.yaml'
SCHEDULE_CONFIG = CONFIG_DIR / 'schedule.yaml'
TELEMETRY_CONFIG = CONFIG_DIR / 'telemetry.yaml'
DATA_CONFIG = CONFIG_DIR / 'data.yaml'
BROKER_CONFIG = CONFIG_DIR / 'broker.yaml'
METRICS_CONFIG = CONFIG_DIR / 'metrics.yaml'
LOGS_CONFIG = CONFIG_DIR / 'logs.yaml'
REPORTS_CONFIG = CONFIG_DIR / 'reports.yaml'
SAFETY_CONFIG = CONFIG_DIR / 'safety.yaml'
US_HOLIDAYS_CONFIG = CONFIG_DIR / 'us_holidays.json'
US_HALFDAYS_CONFIG = CONFIG_DIR / 'us_halfdays.json'

# Log file paths (LOW PRIORITY)
FILLS_STATE_FILE = LOGS_TRADING_DIR / 'fills_state.jsonl'
RUN_SUMMARIES_FILE = LOGS_AUDIT_DIR / 'run_summaries.jsonl'
SNAPSHOT_CSV_FILE = LOGS_TRADING_DIR / 'snapshots.csv'

# Report file paths (LOW PRIORITY)
# Reports are typically created dynamically, but we provide the base directory


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    directories = [
        DATA_DIR,
        STATE_DIR,
        CONFIG_DIR,
        LOGS_DIR,
        REPORTS_DIR,
        REPLAYS_DIR,
        CACHE_DIR,
        LOGS_TRADING_DIR,
        LOGS_AUDIT_DIR,
        REPORTS_MONTHLY_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Create directories automatically on import
ensure_directories()


def get_log_file(name: str) -> Path:
    """
    Get path to a log file in the logs directory.
    
    Args:
        name: Log file name (e.g., "app.log" or "trading/fills.jsonl")
        
    Returns:
        Absolute Path to the log file
    """
    return LOGS_DIR / name


def get_report_file(name: str) -> Path:
    """
    Get path to a report file in the reports directory.
    
    Args:
        name: Report file name (e.g., "daily_report.html")
        
    Returns:
        Absolute Path to the report file
    """
    return REPORTS_DIR / name


def get_incident_file(date_str: Optional[str] = None) -> Path:
    """
    Get path to an incident log file.
    
    Args:
        date_str: Optional date string (YYYY-MM-DD). If None, uses today's date.
        
    Returns:
        Absolute Path to the incident file
    """
    from datetime import datetime
    if date_str is None:
        date_str = datetime.utcnow().date().isoformat()
    return LOGS_DIR / f"{date_str}_incidents.jsonl"


def get_replay_file(name: str) -> Path:
    """
    Get path to a replay file in the replays directory.
    
    Args:
        name: Replay file name (e.g., "replay_2024-01-10.json")
        
    Returns:
        Absolute Path to the replay file
    """
    return REPLAYS_DIR / name


# Export commonly used paths for convenience
__all__ = [
    # Root and directories
    'PROJECT_ROOT',
    'DATA_DIR',
    'STATE_DIR',
    'CONFIG_DIR',
    'LOGS_DIR',
    'REPORTS_DIR',
    'REPLAYS_DIR',
    'CACHE_DIR',
    'LOGS_TRADING_DIR',
    'LOGS_AUDIT_DIR',
    'REPORTS_MONTHLY_DIR',
    
    # State files (HIGH PRIORITY)
    'RUN_LOCK_FILE',
    'POSITIONS_FILE',
    'KILL_SWITCH_FILE',
    'REGIME_STATE_FILE',
    'ORDER_WAL_FILE',
    'TRADING_STATE_FILE',
    
    # Guardian files
    'GUARDIAN_HEARTBEAT_FILE',
    
    # Config files
    'RISK_CONFIG',
    'EXPOSURE_CONFIG',
    'SCHEDULE_CONFIG',
    'TELEMETRY_CONFIG',
    'DATA_CONFIG',
    'BROKER_CONFIG',
    'METRICS_CONFIG',
    'LOGS_CONFIG',
    'REPORTS_CONFIG',
    'SAFETY_CONFIG',
    'US_HOLIDAYS_CONFIG',
    'US_HALFDAYS_CONFIG',
    
    # Log files
    'FILLS_STATE_FILE',
    'RUN_SUMMARIES_FILE',
    'SNAPSHOT_CSV_FILE',
    
    # Helper functions
    'get_log_file',
    'get_report_file',
    'get_incident_file',
    'get_replay_file',
    'ensure_directories',
]

