# Production Execution Rule

## Problem Statement

The `run_http_trigger.py` module contained legacy "script mode" compatibility code that:
1. Detected execution context (script vs module)
2. Added `regimeflex` to `sys.path` when run as script
3. Used top-level imports (`from engine.runner import ...`) instead of package imports
4. Caused `ImportError` when `runner.py` tried to use relative imports

**Root Cause**: When imported as `engine.runner` (top-level), Python doesn't recognize it as part of a package, so relative imports fail.

## Solution: Enforce Package-Only Execution

### Production Rule

**The HTTP trigger server MUST ONLY be executed as a package component:**

```bash
# ✅ CORRECT - Production execution
python -m regimeflex http

# ✅ CORRECT - Direct module execution (also works)
python -m regimeflex.scripts.run_http_trigger

# ❌ INCORRECT - Direct script execution (now blocked)
python regimeflex/scripts/run_http_trigger.py
```

### Changes Made

1. **Removed script mode detection logic**
   - No more conditional imports
   - No more `sys.path` manipulation
   - No more top-level imports

2. **Enforced absolute imports only**
   - All imports use `from regimeflex.engine...`
   - All imports use `from regimeflex.scripts...`
   - No relative imports that depend on execution context

3. **Added execution guard**
   - `if __name__ == "__main__"` now exits with error
   - Prevents accidental direct script execution
   - Provides clear error message

4. **Updated documentation**
   - Module docstring explains production rule
   - Function docstrings clarify execution method

## Why This Works

When executed as `python -m regimeflex http`:
1. Python treats `regimeflex` as a package
2. `__package__` is set to `"regimeflex"`
3. All imports resolve correctly:
   - `from regimeflex.engine.runner import ...` ✅
   - `runner.py` can use `from .identity import ...` ✅ (relative imports work)
4. No path manipulation needed

## Verification

### Test Production Execution
```bash
# Should work
python -m regimeflex http

# Should fail with clear error
python regimeflex/scripts/run_http_trigger.py
```

### Expected Behavior

**Module Execution (✅ Works)**:
```bash
$ python -m regimeflex http
[INFO] Starting HTTP server on 0.0.0.0:5000
 * Serving Flask app 'regimeflex.scripts.run_http_trigger'
 * Running on http://0.0.0.0:5000
```

**Direct Script Execution (❌ Blocked)**:
```bash
$ python regimeflex/scripts/run_http_trigger.py
[ERROR] ERROR: This module must be executed as a package component.
  Use: python -m regimeflex http
  NOT: python regimeflex/scripts/run_http_trigger.py
```

## PM2 Configuration

Ensure PM2 uses module execution:

```javascript
{
    name: "regimeflex",
    script: "python",
    args: "-m regimeflex http",  // ✅ Module execution
    cwd: "./",
    // ...
}
```

**NOT**:
```javascript
{
    script: "regimeflex/scripts/run_http_trigger.py",  // ❌ Direct script
}
```

## Benefits

1. **No Import Errors**: Package context ensures all imports work
2. **Consistent Behavior**: Same execution method in dev and production
3. **Clear Errors**: Direct script execution fails with helpful message
4. **Production Ready**: Works reliably in PM2, Railway, systemd

## Migration Guide

If you have any scripts or documentation that reference direct execution:

**Before**:
```bash
python regimeflex/scripts/run_http_trigger.py
```

**After**:
```bash
python -m regimeflex http
```

## Summary

- ✅ Removed script mode compatibility code
- ✅ Enforced package-only execution
- ✅ All imports use absolute package paths
- ✅ Clear error message for incorrect usage
- ✅ Production-ready and reliable

**The HTTP trigger server now follows Python packaging best practices and works consistently in all production environments.**

