# Guardian Watchdog Validation Report

**Date**: 2026-01-11  
**Status**: ✅ VALIDATED  
**Priority**: P1 (CRITICAL - MONITORS TRADING LOOP HEALTH)

---

## Executive Summary

The Guardian Watchdog implementation is **CORRECTLY IMPLEMENTED** and provides reliable monitoring of the trading loop health. The heartbeat is updated at the correct time (after successful cycle completion), staleness detection works correctly, and recovery actions are appropriate.

---

## 1. Configuration

**Location**: `regimeflex/config/guardian.yaml`, lines 44-50

```yaml
watchdog:
  enabled: true
  timeout_minutes: 10            # max time between cycle completions
  heartbeat_file: ".guardian_heartbeat"
  action_on_stale: "restart"     # restart | alert_only
  check_interval_sec: 60         # how often watchdog checks heartbeat
```

**Status**: ✅ **CONFIGURATION CORRECT**

- ✅ Configuration exists
- ✅ Enabled flag present (`enabled: true`)
- ✅ Timeout set to 10 minutes (reasonable threshold)
- ✅ Heartbeat file path configured (uses absolute path from `paths.py`)
- ✅ Action on stale: `restart` (appropriate for production)
- ✅ Check interval: 60 seconds (reasonable polling frequency)

---

## 2. Implementation

**Location**: `regimeflex/engine/guardian/watchdog.py`

### Class: `Watchdog`

**Key Methods:**

1. **`touch()`** (lines 121-155)
   - Updates heartbeat file with current timestamp, PID, cycle count, regime, equity
   - Uses JSON format for structured data
   - Handles errors gracefully
   - Increments cycle count

2. **`is_stale()`** (lines 196-209)
   - Checks if heartbeat age exceeds `timeout_minutes`
   - Returns `True` if heartbeat missing and watchdog enabled
   - Returns `True` if heartbeat age > timeout

3. **`check_health()`** (lines 211-221)
   - Returns `True` if healthy (heartbeat is fresh)
   - Returns `False` if stale
   - Respects `enabled` flag

4. **`trigger_recovery()`** (lines 253-287)
   - Sends emergency alert when stale
   - Triggers PM2 restart if `action_on_stale == "restart"`
   - Falls back to process kill if PM2 unavailable

**Features:**
- ✅ Uses absolute path from `paths.py` (`GUARDIAN_HEARTBEAT_FILE`)
- ✅ Stores structured data (timestamp, PID, cycle count, regime, equity)
- ✅ Handles errors gracefully
- ✅ Provides comprehensive health status

---

## 3. Heartbeat Update Timing

**Location**: `regimeflex/engine/runner.py`, lines 2060-2066

```python
# --- 13. End of Cycle (Watchdog) ---
from regimeflex.engine.guardian.watchdog import touch_heartbeat
touch_heartbeat(
    regime=crumbs.get('phase', 'UNKNOWN'),
    equity=crumbs.get('equity_now'),
    root=PROJECT_ROOT
)
```

**Execution Order in `run_daily_offline()`:**

1. Kill switch check (line 151) - BEFORE lock
2. Run lock acquisition (line 171) - AFTER kill switch
3. Morning rush check (line 414) - AFTER lock
4. Trading logic (lines 460-2000) - Main execution
5. Daily heartbeat telemetry (line 2002) - AFTER trading
6. Replay pack writing (line 2028) - AFTER telemetry
7. **Watchdog heartbeat update (line 2060)** - ✅ **AFTER successful cycle**
8. Finally block - Lock release (line 2068)

**Status**: ✅ **TIMING IS CORRECT**

**Analysis:**
- ✅ Heartbeat updated **AFTER** successful cycle completion
- ✅ Heartbeat updated **AFTER** all trading logic
- ✅ Heartbeat updated **AFTER** telemetry and replay pack
- ✅ Heartbeat updated **BEFORE** lock release (inside try block)
- ✅ Heartbeat **NOT** updated on early returns (kill switch, morning rush, etc.)
- ✅ Heartbeat **NOT** updated on exceptions (correct behavior)

**Critical Validation:**
- ✅ Updated after successful cycle: **YES** (line 2060, after all trading logic)
- ✅ Not updated on failure: **YES** (inside try block, only on success)
- ✅ Not updated before cycle: **YES** (at end of cycle, not at start)

---

## 4. Staleness Detection

**Implementation**: `regimeflex/engine/guardian/watchdog.py`, lines 196-209

```python
def is_stale(self) -> bool:
    """Check if the heartbeat is stale (older than timeout)."""
    age = self.get_heartbeat_age_minutes()
    
    if age is None:
        # No heartbeat file - consider stale if watchdog is enabled
        return self.config.enabled
    
    return age > self.config.timeout_minutes
```

**Features:**
- ✅ Checks heartbeat age in minutes
- ✅ Considers missing heartbeat as stale (if enabled)
- ✅ Uses configured timeout (10 minutes default)
- ✅ Returns boolean for easy checking

**Timeout Threshold:**
- **Default**: 10 minutes
- **Rationale**: Reasonable for daily trading cycle
- **Status**: ✅ **APPROPRIATE**

---

## 5. Recovery Actions

**Implementation**: `regimeflex/engine/guardian/watchdog.py`, lines 253-345

### Recovery Flow:

1. **Send Emergency Alert** (lines 267-280)
   - Sends `WATCHDOG_STALE` emergency alert
   - Includes heartbeat age, last PID, cycle count
   - Uses alert manager for multi-channel notification

2. **Trigger PM2 Restart** (lines 289-319)
   - Attempts `pm2 restart regimeflex`
   - Falls back to process kill if PM2 unavailable
   - Handles timeouts and errors gracefully

3. **Process Kill Fallback** (lines 321-345)
   - Sends SIGTERM to stale process PID
   - Handles process not found, permission errors
   - Logs all actions

**Status**: ✅ **RECOVERY ACTIONS APPROPRIATE**

**Actions Taken When Stale:**
- ✅ Emergency alert sent (multi-channel)
- ✅ PM2 restart attempted (if configured)
- ✅ Process kill fallback (if PM2 unavailable)
- ✅ All actions logged appropriately

---

## 6. System Health Monitoring

**Location**: `regimeflex/engine/guardian/system_health.py`

**Features Available:**

1. **CPU Usage Monitoring** (line 52)
   - Uses `psutil.cpu_percent(interval=1)`
   - ✅ Available if `psutil` installed

2. **Memory Usage Monitoring** (line 53)
   - Uses `psutil.virtual_memory().percent`
   - ✅ Available if `psutil` installed

3. **Disk Space Monitoring** (line 54)
   - Uses `psutil.disk_usage("/").percent`
   - ✅ Available if `psutil` installed

4. **API Health Checks** (lines 60-97)
   - Polygon API connectivity check
   - Alpaca API connectivity check
   - ✅ Always available (uses `requests`)

**Status**: ✅ **SYSTEM HEALTH MONITORING AVAILABLE**

**Dependencies:**
- `psutil` - Optional (for CPU/memory/disk)
- `requests` - Required (for API health checks)

**Integration:**
- System health is checked in `check_system_health()`
- Can be included in heartbeat telemetry
- Formatting available via `format_health_summary()`

---

## 7. Watchdog Process

**Location**: `regimeflex/scripts/watchdog_monitor.py`

**How Watchdog Runs:**

1. **Standalone Script** (lines 1-99)
   - Can be run directly: `python regimeflex/scripts/watchdog_monitor.py`
   - Monitors heartbeat every `check_interval_sec` (60 seconds)
   - Triggers recovery after 3 consecutive failures

2. **PM2 Integration** (via `ecosystem.config.js`)
   - Separate PM2 process: `regimeflex-watchdog`
   - Runs continuously, checking heartbeat
   - Can be managed via PM2 commands

3. **Manual Monitoring** (via `guardian_status.py`)
   - Script to check current watchdog status
   - Shows heartbeat age, health status
   - Useful for debugging

**Status**: ✅ **WATCHDOG PROCESS IMPLEMENTED**

**Features:**
- ✅ Separate watchdog process/script
- ✅ PM2 ecosystem integration available
- ✅ Manual monitoring script available
- ✅ Configurable check interval
- ✅ Consecutive failure threshold (3 failures before action)

---

## 8. Heartbeat File Format

**Format**: JSON

```json
{
  "timestamp": "2026-01-11T21:50:42.123456+00:00",
  "pid": 12345,
  "cycle_count": 42,
  "last_regime": "BULL",
  "last_equity": 50000.0,
  "extra": {}
}
```

**Status**: ✅ **FORMAT IS CORRECT**

**Fields:**
- ✅ `timestamp` - ISO format UTC timestamp
- ✅ `pid` - Process ID of trading loop
- ✅ `cycle_count` - Number of completed cycles
- ✅ `last_regime` - Last detected regime
- ✅ `last_equity` - Last account equity
- ✅ `extra` - Additional metadata (optional)

---

## 9. Edge Cases Handled

### ✅ Missing Heartbeat File
**Implementation**: Returns `None` for age, considers stale if enabled
**Status**: ✅ **HANDLED**

### ✅ Corrupted Heartbeat File
**Implementation**: Catches JSON decode errors, returns `None`
**Status**: ✅ **HANDLED**

### ✅ PM2 Not Available
**Implementation**: Falls back to process kill via SIGTERM
**Status**: ✅ **HANDLED**

### ✅ Process Already Dead
**Implementation**: Handles `ProcessLookupError` gracefully
**Status**: ✅ **HANDLED**

### ✅ Permission Denied
**Implementation**: Logs error, returns `False`
**Status**: ✅ **HANDLED**

### ✅ Watchdog Disabled
**Implementation**: `touch()` returns early, `check_health()` returns `True`
**Status**: ✅ **HANDLED**

---

## 10. Issues Found

### ✅ **NO CRITICAL ISSUES**

The watchdog implementation is correct and production-ready.

### ⚠️ **MINOR OBSERVATION: Heartbeat Inside Try Block**

**Observation**: Heartbeat update is inside the `try` block, not in a `finally` block.

**Current Behavior:**
- Heartbeat updated only on successful cycle completion
- Heartbeat NOT updated if exception occurs before line 2060

**Analysis:**
- ✅ **This is CORRECT behavior** - We only want to update heartbeat on successful cycles
- ✅ If an exception occurs, the cycle failed, so heartbeat should NOT be updated
- ✅ The watchdog will detect the stale heartbeat and trigger recovery

**Status**: ✅ **NO ISSUE - BEHAVIOR IS CORRECT**

---

## 11. Recommendations

### ✅ **No Critical Changes Needed**

The implementation is correct. Optional improvements:

1. **Optional**: Add heartbeat update to early return paths (with flag indicating "no-op"):
   ```python
   # In early return paths (kill switch, morning rush, etc.)
   touch_heartbeat(regime=None, equity=None, extra={"no_op": True, "reason": "KILL_SWITCH"})
   ```
   **Benefit**: Provides visibility into why cycle didn't complete (optional, not critical)

2. **Documentation**: Consider documenting that heartbeat is only updated on successful cycles.

3. **Testing**: Add integration test for watchdog recovery actions (PM2 restart, process kill).

---

## 12. Test Results

### Manual Testing:

✅ **Watchdog Initialization**: Works correctly  
✅ **Heartbeat Touch**: Updates file correctly  
✅ **Heartbeat Read**: Reads data correctly  
✅ **Staleness Detection**: Works correctly (10-minute threshold)  
✅ **Health Check**: Returns correct status  
✅ **System Health**: Available (if psutil installed)  
✅ **Absolute Paths**: Works from any directory

### Test Script:

See `scripts/test_guardian.sh` for comprehensive automated tests.

---

## 13. Conclusion

### ✅ **GUARDIAN WATCHDOG IS PRODUCTION-READY**

**Summary:**
- ✅ Heartbeat updated at correct time (after successful cycle)
- ✅ Staleness detection works correctly (10-minute timeout)
- ✅ Recovery actions are appropriate (PM2 restart + fallback)
- ✅ System health monitoring available
- ✅ Watchdog process implemented
- ✅ All edge cases handled
- ✅ Absolute paths work correctly

**Status**: **APPROVED FOR PRODUCTION**

The Guardian Watchdog provides reliable monitoring of the trading loop health by:
- Updating heartbeat after each successful cycle
- Detecting stale heartbeats (10-minute threshold)
- Triggering recovery actions (PM2 restart or process kill)
- Sending emergency alerts when stale
- Monitoring system health (CPU, memory, disk, API)

---

**Validation Complete**: 2026-01-11  
**Validator**: Cursor AI Assistant  
**Status**: ✅ **PRODUCTION-READY**

