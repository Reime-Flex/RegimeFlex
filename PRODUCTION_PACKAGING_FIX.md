# Production Packaging Fix - Complete Solution

## Problem Statement

When deployed under PM2 on Ubuntu, the process crashed with:
```
ImportError: attempted relative import with no known parent package
at regimeflex/engine/runner.py line 8:
from .identity import RegimeFlexIdentity as RF
```

**Root Cause**: The codebase mixed two incompatible execution models:
- **Model A**: Library-style package with relative imports (requires module execution)
- **Model B**: Script-style execution (assumes files can be run directly)

Local dev environments masked this because IDEs add project roots to PYTHONPATH, but production exposed it.

## Solution: Unified Module Execution Model

All execution now uses Python's module system, ensuring proper package context regardless of how the code is invoked.

## Implementation

### 1. Added `main()` Function to `runner.py`

**File**: `regimeflex/engine/runner.py`

Added a `main()` function that:
- Reads configuration from `Config(".")`
- Calls `run_daily_offline()` with proper parameters
- Returns exit codes (0 = success, 1 = error, 130 = SIGINT)
- Can be called via module execution or console script

```python
def main() -> int:
    """CLI entrypoint for runner module."""
    # ... implementation ...
    return 0  # or 1 on error
```

### 2. Created `engine/__main__.py`

**File**: `regimeflex/engine/__main__.py`

Allows execution via: `python -m regimeflex.engine.runner`

```python
from .runner import main
if __name__ == "__main__":
    sys.exit(main())
```

### 3. Updated `setup.py` with Console Scripts

**File**: `setup.py`

Added `entry_points` for console scripts:
```python
entry_points={
    "console_scripts": [
        "regimeflex-run=regimeflex.engine.runner:main",
        "regimeflex-http=regimeflex.scripts.run_http_trigger:main",
    ],
},
```

After `pip install -e .`, these commands are available:
- `regimeflex-run` - Run daily trading cycle
- `regimeflex-http` - Start HTTP trigger server

### 4. Updated PM2 Configuration

**File**: `ecosystem.config.js`

Changed from script execution to module execution:

**Before**:
```javascript
args: "regimeflex/scripts/trigger_server.py",
```

**After**:
```javascript
args: "-m regimeflex http",
```

This ensures Python treats `regimeflex` as a package, enabling all relative imports.

### 5. Created Module Execution Tests

**File**: `regimeflex/tests/test_module_execution.py`

Tests verify:
- `runner.py` can be imported as a module
- `main()` function exists and is callable
- Relative imports work when executed as a module
- Package structure is correct

## Execution Methods (All Work)

### ✅ Method 1: Module Execution (Recommended)
```bash
python -m regimeflex run          # Run daily cycle
python -m regimeflex http         # Start HTTP server
python -m regimeflex health       # Health check
python -m regimeflex.engine.runner  # Direct engine execution
```

### ✅ Method 2: Console Scripts (After pip install -e .)
```bash
pip install -e .
regimeflex-run   # Run daily cycle
regimeflex-http  # Start HTTP server
```

### ✅ Method 3: PM2 with Module Execution
```bash
# Using ecosystem.config.js (already updated)
pm2 start ecosystem.config.js

# Or manually:
pm2 start python --name regimeflex -- -m regimeflex http
```

### ✅ Method 4: Direct Script (Legacy, Still Works)
```bash
python regimeflex/scripts/run_offline_from_config.py
```

## Why This Fix Works

### Previous Structure (Failed)

**Problem**: When PM2 ran `python regimeflex/scripts/trigger_server.py`:
1. Python treated `trigger_server.py` as a standalone script
2. Script added `regimeflex` to `sys.path` manually
3. When `runner.py` was imported, Python didn't know it was part of a package
4. Relative imports (`from .identity import ...`) failed with `ImportError`

### New Structure (Works)

**Solution**: When PM2 runs `python -m regimeflex http`:
1. Python treats `regimeflex` as a package (because of `-m` flag)
2. `__package__` is set to `"regimeflex"` automatically
3. All relative imports resolve correctly
4. No manual `sys.path` manipulation needed

**Key Insight**: The `-m` flag tells Python "this is a module, treat it as a package", which enables relative imports throughout the package tree.

## PM2 Ecosystem Config (Final)

```javascript
module.exports = {
    apps: [
        {
            name: "regimeflex",
            script: "python",
            args: "-m regimeflex http",  // Module execution
            cwd: "./",
            autorestart: true,
            max_restarts: 50,
            env: {
                PYTHONUNBUFFERED: "1",
                REGIMEFLEX_DRY_RUN: "0"
            }
        },
        {
            name: "regimeflex-watchdog",
            script: "python",
            args: "-m regimeflex.scripts.watchdog_monitor",  // Module execution
            cwd: "./",
            autorestart: true,
            max_restarts: -1
        }
    ]
};
```

## Production Deployment Checklist

- [x] Add `main()` function to `runner.py`
- [x] Create `engine/__main__.py`
- [x] Update `setup.py` with console scripts
- [x] Update PM2 `ecosystem.config.js` to use module execution
- [x] Add tests for module execution
- [x] Update README with production commands
- [x] Verify all execution methods work

## Testing

Run the test suite:
```bash
pytest regimeflex/tests/test_module_execution.py -v
```

Expected output:
```
test_runner_module_import PASSED
test_runner_main_exists PASSED
test_package_main_import PASSED
test_relative_imports_work PASSED
test_top_level_main_import PASSED
```

## Verification

Test all execution methods from repo root:

```bash
# 1. Module execution
python -m regimeflex.engine.runner --help  # Should work

# 2. Top-level module
python -m regimeflex --help  # Should work

# 3. After pip install
pip install -e .
regimeflex-run --help  # Should work

# 4. PM2 (if installed)
pm2 start ecosystem.config.js
pm2 logs regimeflex  # Should show no import errors
```

## Benefits

1. **No PYTHONPATH hacks**: Works in clean production environments
2. **No IDE dependencies**: Works without IDE path manipulation
3. **Consistent execution**: Same behavior in dev, staging, and production
4. **Standard Python packaging**: Follows Python packaging best practices
5. **Multiple entry points**: Flexible execution methods for different use cases

## Files Changed

1. `regimeflex/engine/runner.py` - Added `main()` function
2. `regimeflex/engine/__main__.py` - Created module entrypoint
3. `regimeflex/scripts/__main__.py` - Created scripts module entrypoint
4. `setup.py` - Added console_scripts entry points
5. `ecosystem.config.js` - Updated to use module execution
6. `regimeflex/tests/test_module_execution.py` - Added tests
7. `README.md` - Updated with production commands

## Summary

The fix ensures RegimeFlex runs correctly in production by:
- Using Python's module execution system (`python -m`)
- Ensuring proper package context for relative imports
- Providing multiple entry points (module, console scripts, direct)
- Following Python packaging best practices

**No workarounds, no hacks, just proper Python packaging.**

