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
LOGS_DECAY_DIR = LOGS_DIR / 'decay'
LOGS_INCIDENTS_DIR = LOGS_DIR / 'incidents'
REPORTS_MONTHLY_DIR = REPORTS_DIR / 'monthly'

# State file paths (HIGH PRIORITY - critical for operation)
RUN_LOCK_FILE = STATE_DIR / 'run.lock'
POSITIONS_FILE = STATE_DIR / 'positions.json'
KILL_SWITCH_FILE = STATE_DIR / 'kill_switch.json'
KILL_SWITCH_FLAG_FILE = CONFIG_DIR / 'kill_switch.flag'  # Flag file used by killswitch.py
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
DAILY_SNAPSHOT_CSV = LOGS_TRADING_DIR / 'daily_snapshot.csv'  # Used by pnl.py
# Note: Incidents are stored in LOGS_INCIDENTS_DIR with date-based filenames

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
        LOGS_DECAY_DIR,
        LOGS_INCIDENTS_DIR,
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
    return LOGS_INCIDENTS_DIR / f"{date_str}_incidents.jsonl"


def get_replay_file(name: str) -> Path:
    """
    Get path to a replay file in the replays directory.
    
    Args:
        name: Replay file name (e.g., "replay_2024-01-10.json")
        
    Returns:
        Absolute Path to the replay file
    """
    return REPLAYS_DIR / name


def print_paths() -> None:
    """
    Diagnostic function to print all path constants.
    
    Useful for debugging path issues and verifying paths are correct.
    """
    print("=" * 70)
    print("RegimeFlex Path Constants")
    print("=" * 70)
    
    print("\n[Root]")
    print(f"  PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"  Is absolute: {PROJECT_ROOT.is_absolute()}")
    print(f"  Exists: {PROJECT_ROOT.exists()}")
    
    print("\n[Directories]")
    directories = {
        'DATA_DIR': DATA_DIR,
        'STATE_DIR': STATE_DIR,
        'CONFIG_DIR': CONFIG_DIR,
        'LOGS_DIR': LOGS_DIR,
        'REPORTS_DIR': REPORTS_DIR,
        'REPLAYS_DIR': REPLAYS_DIR,
        'CACHE_DIR': CACHE_DIR,
        'LOGS_TRADING_DIR': LOGS_TRADING_DIR,
        'LOGS_AUDIT_DIR': LOGS_AUDIT_DIR,
        'LOGS_DECAY_DIR': LOGS_DECAY_DIR,
        'LOGS_INCIDENTS_DIR': LOGS_INCIDENTS_DIR,
        'REPORTS_MONTHLY_DIR': REPORTS_MONTHLY_DIR,
    }
    for name, path in directories.items():
        print(f"  {name}: {path}")
        print(f"    Absolute: {path.is_absolute()}, Exists: {path.exists()}")
    
    print("\n[State Files (HIGH PRIORITY)]")
    state_files = {
        'RUN_LOCK_FILE': RUN_LOCK_FILE,
        'POSITIONS_FILE': POSITIONS_FILE,
        'KILL_SWITCH_FILE': KILL_SWITCH_FILE,
        'KILL_SWITCH_FLAG_FILE': KILL_SWITCH_FLAG_FILE,
        'REGIME_STATE_FILE': REGIME_STATE_FILE,
        'ORDER_WAL_FILE': ORDER_WAL_FILE,
        'TRADING_STATE_FILE': TRADING_STATE_FILE,
    }
    for name, path in state_files.items():
        print(f"  {name}: {path}")
        print(f"    Absolute: {path.is_absolute()}, Exists: {path.exists()}")
    
    print("\n[Guardian Files]")
    print(f"  GUARDIAN_HEARTBEAT_FILE: {GUARDIAN_HEARTBEAT_FILE}")
    print(f"    Absolute: {GUARDIAN_HEARTBEAT_FILE.is_absolute()}, Exists: {GUARDIAN_HEARTBEAT_FILE.exists()}")
    
    print("\n[Config Files (MEDIUM PRIORITY)]")
    config_files = {
        'RISK_CONFIG': RISK_CONFIG,
        'EXPOSURE_CONFIG': EXPOSURE_CONFIG,
        'SCHEDULE_CONFIG': SCHEDULE_CONFIG,
        'TELEMETRY_CONFIG': TELEMETRY_CONFIG,
        'DATA_CONFIG': DATA_CONFIG,
        'BROKER_CONFIG': BROKER_CONFIG,
        'METRICS_CONFIG': METRICS_CONFIG,
        'LOGS_CONFIG': LOGS_CONFIG,
        'REPORTS_CONFIG': REPORTS_CONFIG,
        'SAFETY_CONFIG': SAFETY_CONFIG,
        'US_HOLIDAYS_CONFIG': US_HOLIDAYS_CONFIG,
        'US_HALFDAYS_CONFIG': US_HALFDAYS_CONFIG,
    }
    for name, path in config_files.items():
        print(f"  {name}: {path}")
        print(f"    Absolute: {path.is_absolute()}, Exists: {path.exists()}")
    
    print("\n[Log Files (LOW PRIORITY)]")
    log_files = {
        'FILLS_STATE_FILE': FILLS_STATE_FILE,
        'RUN_SUMMARIES_FILE': RUN_SUMMARIES_FILE,
        'SNAPSHOT_CSV_FILE': SNAPSHOT_CSV_FILE,
        'DAILY_SNAPSHOT_CSV': DAILY_SNAPSHOT_CSV,
    }
    for name, path in log_files.items():
        print(f"  {name}: {path}")
        print(f"    Absolute: {path.is_absolute()}, Exists: {path.exists()}")
    
    print("\n" + "=" * 70)


# Allow running as script: python -m regimeflex.config.paths
if __name__ == '__main__':
    print_paths()


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
    'KILL_SWITCH_FLAG_FILE',
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
    'DAILY_SNAPSHOT_CSV',
    'LOGS_DECAY_DIR',
    'LOGS_INCIDENTS_DIR',
    
    # Helper functions
    'get_log_file',
    'get_report_file',
    'get_incident_file',
    'get_replay_file',
    'ensure_directories',
    'print_paths',
]

