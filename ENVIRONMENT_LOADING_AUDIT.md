# Environment Loading Audit Report

**Date**: 2026-01-10  
**Priority**: P0 (Blocks all other work)  
**Status**: Complete

---

## Executive Summary

The RegimeFlex codebase uses a **centralized environment loading pattern** via `regimeflex.engine.env.load_env()`. The `load_dotenv()` function is called **only once** in the codebase, within the `load_env()` function. However, **many modules access environment variables directly** without ensuring `load_env()` has been called first.

**Key Finding**: The codebase relies on **explicit calls to `load_env()`** rather than automatic .env loading. If `load_env()` is not called before accessing environment variables, the .env file will not be loaded.

---

## 1. Dotenv Imports

### Files Importing dotenv

**Total: 2 files**

1. **`regimeflex/engine/env.py`** (Line 3)
   ```python
   from dotenv import load_dotenv
   ```
   - **Status**: ✅ Active import (used in `load_env()` function)

2. **`regimeflex/docs/DEVELOPMENT.md`** (Line 594)
   ```python
   from dotenv import load_dotenv
   ```
   - **Status**: 📄 Documentation only (example code)

---

## 2. load_dotenv() Calls

### Active Calls

**Total: 1 active call**

#### `regimeflex/engine/env.py` (Line 20)

**Function**: `load_env(dotenv_path: str = ".env") -> Env`

**Context**:
```python
def load_env(dotenv_path: str = ".env") -> Env:
    # Load .env if present, otherwise continue silently.
    if Path(dotenv_path).exists():
        load_dotenv(dotenv_path, override=False)  # ← Line 20
    return Env(
        alpaca_key=os.getenv("ALPACA_KEY"),
        alpaca_secret=os.getenv("ALPACA_SECRET"),
        # ... more env vars
    )
```

**Arguments**:
- `dotenv_path`: Defaults to `".env"` (relative to current working directory)
- `override=False`: Does not override existing environment variables

**Behavior**:
- Only loads `.env` if file exists
- Fails silently if `.env` doesn't exist
- Does not override existing `os.environ` values

---

## 3. Environment Variable Accesses

### Summary Statistics

| Pattern | Count | Files |
|---------|-------|-------|
| `os.getenv(...)` | 12 occurrences | 3 files |
| `os.environ.get(...)` | 14 occurrences | 5 files |
| `os.environ[...]` | 0 occurrences | 0 files |
| **Total** | **26 occurrences** | **7 files** |

### Files Accessing Environment Variables

1. `regimeflex/engine/env.py` - Uses `os.getenv()` (8 times)
2. `regimeflex/engine/exec_alpaca.py` - Uses `os.getenv()` and `os.environ.get()` (4 times)
3. `regimeflex/engine/guardian/alerting.py` - Uses `os.environ.get()` (8 times)
4. `regimeflex/scripts/run_http_trigger.py` - Uses `os.environ.get()` (1 time)
5. `regimeflex/scripts/trigger_server.py` - Uses `os.environ.get()` (3 times)
6. `regimeflex/engine/env_watchdog.py` - Uses `os.environ.get()` (1 time)
7. `regimeflex/docs/DEVELOPMENT.md` - Documentation example (1 time)

### Environment Variable Names (First 10+)

**From `regimeflex/engine/env.py`** (via `load_env()`):
1. `ALPACA_KEY`
2. `ALPACA_SECRET`
3. `ALPACA_LIVE_KEY`
4. `ALPACA_LIVE_SECRET`
5. `POLYGON_KEY`
6. `TELEGRAM_BOT_TOKEN`
7. `TELEGRAM_CHAT_ID`
8. `ENV` (defaults to "dev")

**From `regimeflex/engine/exec_alpaca.py`**:
9. `ALPACA_KEY` (also checks `APCA_API_KEY_ID`)
10. `ALPACA_SECRET` (also checks `APCA_API_SECRET_KEY`)
11. `ALPACA_BASE_URL` (also checks `APCA_API_BASE_URL`)
12. `REGIMEFLEX_DRY_RUN`

**From `regimeflex/engine/guardian/alerting.py`**:
13. `DISCORD_WEBHOOK_URL` (dynamic env var name)
14. `TELEGRAM_BOT_TOKEN`
15. `TELEGRAM_CHAT_ID`
16. `GUARDIAN_EMERGENCY_PHONE` (dynamic env var name)
17. `TWILIO_ACCOUNT_SID`
18. `TWILIO_AUTH_TOKEN`
19. `TWILIO_FROM_NUMBER`
20. `GUARDIAN_EMERGENCY_WEBHOOK`

**From `regimeflex/scripts/run_http_trigger.py`**:
21. `PORT`

**From `regimeflex/scripts/trigger_server.py`**:
22. `REGIMEFLEX_TRIGGER_TOKEN` (dynamic env var name)
23. `PORT`
24. `REGIMEFLEX_TRIGGER_PORT`
25. `REGIMEFLEX_TRIGGER_HOST`

**From `regimeflex/engine/env_watchdog.py`**:
26. Various env vars (checked dynamically)

---

## 4. Specific Files Check

### 4.1 `regimeflex/__init__.py`

**Status**: ✅ Exists

**Contents**:
```python
"""
RegimeFlex Trading System

A systematic trading system with regime detection, risk management,
and real broker integration.
"""

__version__ = "30.0.0"
__author__ = "RegimeFlex Team"
```

**Environment Loading**: ❌ No environment loading in `__init__.py`

---

### 4.2 `regimeflex/__main__.py`

**Status**: ✅ Exists

**Contents** (first 30 lines):
```python
"""
RegimeFlex Package Entrypoint

This allows RegimeFlex to be executed as a Python module:
    python -m regimeflex [command] [args...]

Uses absolute imports for location-independent execution.
"""

import sys
import os
from pathlib import Path

# Ensure we're running from the correct context
# When run as 'python -m regimeflex', Python sets __package__ correctly
# and all relative imports will work

def main():
    """Main entrypoint for module execution."""
    if len(sys.argv) < 2:
        print("RegimeFlex - Automated TQQQ/SQQQ Swing Trading System")
        print("\nUsage:")
        print("  python -m regimeflex run          # Run daily trading cycle")
        print("  python -m regimeflex http         # Start HTTP trigger server")
        print("  python -m regimeflex health        # Run health check")
        print("  python -m regimeflex <script>     # Run a script from scripts/")
        print("\nFor more options, see:")
        print("  python -m regimeflex --help")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--help" or command == "-h":
        print("RegimeFlex Module Entrypoint")
        print("\nCommands:")
        print("  run              Run daily trading cycle (offline)")
        print("  http             Start HTTP trigger server (for Railway/cron)")
        print("  health           Run full health check")
        print("  <script_name>    Run a script from regimeflex/scripts/")
```

**Environment Loading**: ❌ No environment loading in `__main__.py`

---

### 4.3 `regimeflex/engine/runner.py` (First 30 lines)

**Status**: ✅ Exists

**Contents** (first 30 lines):
```python
from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
from typing import Dict, List
import time
from datetime import date
import pandas as pd

# Absolute imports from regimeflex.engine package
from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.env import load_env
from regimeflex.engine.config import Config
from regimeflex.engine.killswitch import is_killed
from regimeflex.engine.logrotate import rotate_all
from regimeflex.engine.log_rotate import rotate_logs
from regimeflex.engine.pnl import snapshot_from_positions, append_snapshot_csv
from regimeflex.engine.exposure import exposure_allocator, classify_phase
from regimeflex.engine.guardrails import enforce_exposure_caps
from regimeflex.engine.versioning import runtime_versions
from regimeflex.engine.exposure_delta import current_exposure_weights, exposure_delta
from regimeflex.engine.exposure_reason import compute_exposure_diagnostics, format_plan_reason
from regimeflex.engine.symbols import resolve_signal_underlier
from regimeflex.engine.signals import trend_signal, mr_signal, detect_regime, RegimeState
from regimeflex.engine.instruments import resolve_execution_pair
from regimeflex.engine.turnover import enforce_turnover_cap
from regimeflex.engine.reconcile_positions import effective_positions_before
from regimeflex.engine.report_csv import write_change_report
from regimeflex.engine.run_summary import append_run_summary
```

**Environment Loading**: ⚠️ Imports `load_env` but does not call it at module level

---

### 4.4 `regimeflex_entrypoint.py` (First 30 lines)

**Status**: ✅ Exists

**Contents** (first 30 lines):
```python
#!/usr/bin/env python3
"""
RegimeFlex Top-Level Entrypoint

This script ensures RegimeFlex runs with correct package context,
regardless of how it's invoked (direct script, cron, Railway, etc.).

Usage:
    python regimeflex_entrypoint.py <command> [args...]
    
Or make it executable:
    chmod +x regimeflex_entrypoint.py
    ./regimeflex_entrypoint.py <command> [args...]

This entrypoint:
1. Ensures the project root is in sys.path
2. Sets up correct working directory
3. Executes commands via the package module system
"""

import sys
import os
from pathlib import Path

# Find project root (directory containing regimeflex/)
project_root = Path(__file__).parent.absolute()
regimeflex_dir = project_root / "regimeflex"

if not regimeflex_dir.exists():
    print(f"Error: Could not find regimeflex package at {regimeflex_dir}")
    sys.exit(1)

# Add project root to Python path (ensures imports work)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Change to project root for consistent working directory
os.chdir(project_root)
```

**Environment Loading**: ❌ No environment loading in entrypoint

---

## 5. Critical Findings

### 5.1 Environment Loading Pattern

**Current Pattern**:
- `load_dotenv()` is called **only** in `regimeflex.engine.env.load_env()`
- `load_env()` must be **explicitly called** by consuming code
- Many modules access `os.getenv()`/`os.environ.get()` **without** calling `load_env()` first

**Risk**: If `load_env()` is not called before environment variable access, the `.env` file will not be loaded, and variables will be `None` or use defaults.

### 5.2 Modules That Call `load_env()`

**Verified Calls**:
1. `regimeflex/engine/runner.py` - Imports `load_env` (line 13) but **does not call it at module level**
2. `regimeflex/engine/data.py` - Imports `load_env` (line 10)
3. `regimeflex/scripts/show_env.py` - Calls `load_env()` (line 11)

**Potential Issues**:
- `runner.py` imports `load_env` but may not call it before accessing env vars
- Other modules may access env vars without calling `load_env()` first

### 5.3 Direct Environment Variable Access

**Modules accessing env vars without calling `load_env()`**:

1. **`regimeflex/engine/exec_alpaca.py`**
   - Accesses `ALPACA_KEY`, `ALPACA_SECRET`, `ALPACA_BASE_URL`, `REGIMEFLEX_DRY_RUN`
   - Does not call `load_env()` before access

2. **`regimeflex/engine/guardian/alerting.py`**
   - Accesses multiple env vars for notifications
   - Does not call `load_env()` before access

3. **`regimeflex/scripts/run_http_trigger.py`**
   - Accesses `PORT` env var
   - Does not call `load_env()` before access

4. **`regimeflex/scripts/trigger_server.py`**
   - Accesses multiple env vars
   - Does not call `load_env()` before access

### 5.4 .env File Location

**Current Behavior**:
- `load_env()` defaults to `".env"` (relative to current working directory)
- No path resolution - relies on CWD being correct
- Silent failure if `.env` doesn't exist

**Risk**: If script is run from wrong directory, `.env` file won't be found.

---

## 6. Recommendations

### Priority 1: Ensure load_env() is Called Early

**Problem**: Entry points (`__main__.py`, `run_http_trigger.py`) do not call `load_env()`.

**Solution**: Add `load_env()` call at the start of:
- `regimeflex/__main__.py` (in `main()` function)
- `regimeflex/scripts/run_http_trigger.py` (at module level or in `main()`)

### Priority 2: Fix .env Path Resolution

**Problem**: `load_env()` uses relative path `".env"` which depends on CWD.

**Solution**: Update `load_env()` to detect project root and use absolute path:
```python
def load_env(dotenv_path: str | None = None) -> Env:
    if dotenv_path is None:
        # Detect project root
        project_root = detect_project_root()
        dotenv_path = project_root / ".env"
    
    if Path(dotenv_path).exists():
        load_dotenv(dotenv_path, override=False)
    # ... rest of function
```

### Priority 3: Add Environment Loading to Entry Points

**Problem**: No automatic .env loading when module is executed.

**Solution**: Add to `regimeflex/__main__.py`:
```python
def main():
    # Load environment variables first
    from regimeflex.engine.env import load_env
    load_env()  # Ensure .env is loaded before any other code runs
    
    # ... rest of function
```

---

## 7. Conclusion

**Current State**:
- ✅ `load_dotenv()` is properly isolated in `env.py`
- ⚠️ `load_env()` must be explicitly called (not automatic)
- ❌ Entry points do not call `load_env()`
- ❌ Many modules access env vars without ensuring `.env` is loaded
- ⚠️ `.env` path resolution depends on CWD

**Relies on Cursor Auto-Loading?**: **NO** - The codebase does not rely on Cursor's auto-loading. It uses explicit `load_dotenv()` calls, but the calls are **not happening at entry points**, which means `.env` may not be loaded in production unless code explicitly calls `load_env()`.

**Action Required**: Add `load_env()` calls to all entry points to ensure `.env` is loaded before any environment variable access.

