# RegimeFlex Execution Model

## Problem Statement

The original codebase mixed two incompatible execution models:

1. **Model A - Library-style package**: Uses relative imports (`from .identity import ...`), requires execution as `python -m regimeflex.engine.runner`
2. **Model B - Script-style execution**: Assumes files can be run directly (`python regimeflex/scripts/run_http_trigger.py`)

This inconsistency caused import errors in production (Railway) where the execution context differs from local development.

## Solution: Unified Entrypoint System

RegimeFlex now supports **three execution methods**, all of which work correctly:

### Method 1: Module Execution (Recommended for Production)

```bash
python -m regimeflex <command>
```

**Advantages**:
- ✅ Python treats `regimeflex` as a package
- ✅ All relative imports work correctly
- ✅ No path manipulation needed
- ✅ Works consistently across all environments

**Examples**:
```bash
python -m regimeflex run          # Run daily trading cycle
python -m regimeflex http         # Start HTTP server (for Railway)
python -m regimeflex health       # Run health check
```

### Method 2: Top-Level Entrypoint Script

```bash
python regimeflex_entrypoint.py <command>
```

**Advantages**:
- ✅ Works when run from any directory
- ✅ Automatically sets up correct context
- ✅ Delegates to module execution internally
- ✅ Good for cron jobs and automation

**Examples**:
```bash
python regimeflex_entrypoint.py run
python regimeflex_entrypoint.py http
```

### Method 3: Direct Script Execution (Legacy Support)

```bash
python regimeflex/scripts/run_http_trigger.py
```

**Status**: Still works, but scripts now detect execution context and use appropriate imports.

**Note**: This method requires scripts to handle both module and script contexts.

## Implementation Details

### Package Structure

```
regimeflex/
├── __init__.py          # Package marker
├── __main__.py          # Module entrypoint (python -m regimeflex)
├── engine/
│   ├── __init__.py
│   └── runner.py        # Uses relative imports (from .identity import ...)
└── scripts/
    ├── run_http_trigger.py  # Handles both contexts
    └── ...
```

### Import Strategy

**Engine modules** (e.g., `engine/runner.py`):
- Always use relative imports: `from .identity import ...`
- This works when executed via module system

**Script modules** (e.g., `scripts/run_http_trigger.py`):
- Detect execution context:
  ```python
  if __name__ == "__main__":
      # Running as script - use absolute imports
      from engine.identity import ...
  else:
      # Running as module - use relative imports
      from ..engine.identity import ...
  ```

### Railway Configuration

**Current** (`railway.json`):
```json
{
  "startCommand": "python regimeflex/scripts/run_http_trigger.py"
}
```

**Recommended** (more robust):
```json
{
  "startCommand": "python -m regimeflex http"
}
```

Or:
```json
{
  "startCommand": "python regimeflex_entrypoint.py http"
}
```

## Migration Guide

### For Railway Deployment

**Option A** (Recommended): Update `railway.json`:
```json
{
  "startCommand": "python -m regimeflex http"
}
```

**Option B**: Keep current, but ensure scripts handle both contexts (already done).

### For Local Development

**Before**:
```bash
python regimeflex/scripts/run_offline_from_config.py
```

**After** (any of these work):
```bash
python -m regimeflex run
python regimeflex_entrypoint.py run
python regimeflex/scripts/run_offline_from_config.py  # Still works
```

### For Cron Jobs

**Before**:
```bash
0 15 * * 1-5 cd /path/to/RegimeFlex && python regimeflex/scripts/run_offline_from_config.py
```

**After**:
```bash
0 15 * * 1-5 cd /path/to/RegimeFlex && python -m regimeflex run
# OR
0 15 * * 1-5 /path/to/RegimeFlex/regimeflex_entrypoint.py run
```

## Testing Execution Methods

Verify all methods work:

```bash
# Method 1: Module execution
python -m regimeflex --help

# Method 2: Entrypoint script
python regimeflex_entrypoint.py --help

# Method 3: Direct script (if script supports it)
python regimeflex/scripts/run_http_trigger.py --help
```

## Benefits

1. **Consistency**: One clear way to execute (module system)
2. **Reliability**: Works the same in dev, staging, and production
3. **Flexibility**: Multiple entry points for different use cases
4. **Maintainability**: Clear execution model, easier to debug
5. **Production-ready**: No more import errors in Railway

## Future Improvements

1. **Console Scripts**: Add `setup.py` with `entry_points` for `regimeflex` command
2. **Docker**: Use module execution in Dockerfile
3. **Documentation**: Update all docs to use module execution
4. **CI/CD**: Standardize on module execution in CI pipelines

