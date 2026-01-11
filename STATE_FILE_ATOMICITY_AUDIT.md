# State File Atomicity Audit Report

**Date**: 2026-01-10  
**Priority**: P1  
**Status**: Complete

---

## Executive Summary

Audited all state file write operations for atomicity and file locking. Found **6 critical state files** with varying levels of atomicity protection. Some files use atomic write patterns, others need improvement.

---

## State Files Audit

### 1. `positions.json` (HIGH PRIORITY)

**File**: `regimeflex/engine/positions.py`  
**Write Operation**: Line 29

**Current Implementation**:
```python
def save_positions(positions: Dict[str, float]) -> None:
    """Atomically write positions to disk."""
    tmp = POS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({k.upper(): float(v) for k, v in positions.items()}, ensure_ascii=False, indent=2))
    tmp.replace(POS_PATH)
```

**Atomicity**: ✅ **YES** - Uses temp file + rename  
**File Locking**: ❌ **NO** - No fcntl.flock()  
**Risk**: Medium - Could have race condition if two processes write simultaneously

---

### 2. `kill_switch.json` (HIGH PRIORITY)

**File**: `regimeflex/engine/kill_switch_manual.py`  
**Write Operation**: Line 68

**Current Implementation**:
```python
def activate_kill_switch(reason: str = "Manual activation", activated_by: str = "manual") -> bool:
    KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "active": True,
        "reason": reason,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by
    }
    try:
        KILL_SWITCH_FILE.write_text(json.dumps(state, indent=2))
        RF.print_log(f"⛔ KILL SWITCH ACTIVATED: {reason}", "ERROR")
        return True
```

**Atomicity**: ❌ **NO** - Direct write, no temp file  
**File Locking**: ❌ **NO** - No fcntl.flock()  
**Risk**: **HIGH** - Could corrupt file if process crashes mid-write

---

### 3. `regime_state.json` (HIGH PRIORITY)

**File**: `regimeflex/engine/regime_buffer.py`  
**Write Operation**: Line 20

**Current Implementation**:
```python
def save_regime_state(state: Dict[str, Any]) -> None:
    REGIME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGIME_STATE_FILE.write_text(json.dumps(state, indent=2))
```

**Atomicity**: ❌ **NO** - Direct write, no temp file  
**File Locking**: ❌ **NO** - No fcntl.flock()  
**Risk**: **HIGH** - Could corrupt file if process crashes mid-write

---

### 4. `trading_state.json` (HIGH PRIORITY)

**File**: `regimeflex/engine/safety_wrapper.py`  
**Write Operation**: Line 413

**Current Implementation**:
```python
def _save_state(self, state: TradingState) -> None:
    temp_file = self.state_file.with_suffix(".tmp")
    try:
        with open(temp_file, "w") as f:
            if hasattr(fcntl, 'LOCK_EX'):
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(asdict(state), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                json.dump(asdict(state), f, indent=2)
                f.flush()
        temp_file.rename(self.state_file)
```

**Atomicity**: ✅ **YES** - Uses temp file + rename  
**File Locking**: ✅ **YES** - Uses fcntl.flock()  
**Risk**: Low - Properly implemented

---

### 5. `order_wal.jsonl` (HIGH PRIORITY)

**File**: `regimeflex/engine/order_wal.py`  
**Write Operation**: Line 29

**Current Implementation**:
```python
def _append_wal(entry: WALEntry) -> None:
    WAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with WAL_FILE.open("a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(asdict(entry)) + "\n")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Atomicity**: ✅ **YES** - Append-only file (inherently atomic)  
**File Locking**: ✅ **YES** - Uses fcntl.flock()  
**Risk**: Low - Properly implemented (append-only is safe)

---

### 6. `run.lock` (HIGH PRIORITY)

**File**: `regimeflex/engine/run_lock.py`  
**Write Operation**: Line 84

**Current Implementation**:
```python
lock_fd = open(RUN_LOCK_FILE, "w")
if hasattr(fcntl, 'LOCK_EX'):
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
        lock_fd.flush()
        os.fsync(lock_fd.fileno())
```

**Atomicity**: ✅ **YES** - Lock file pattern (inherently atomic)  
**File Locking**: ✅ **YES** - Uses fcntl.flock()  
**Risk**: Low - Properly implemented

---

## Summary Table

| File | Atomic Write | File Locking | Risk Level | Status |
|------|--------------|--------------|------------|--------|
| `positions.json` | ✅ Yes | ❌ No | Medium | ⚠️ Needs locking |
| `kill_switch.json` | ❌ No | ❌ No | **HIGH** | 🔴 Needs fixing |
| `regime_state.json` | ❌ No | ❌ No | **HIGH** | 🔴 Needs fixing |
| `trading_state.json` | ✅ Yes | ✅ Yes | Low | ✅ Good |
| `order_wal.jsonl` | ✅ Yes* | ✅ Yes | Low | ✅ Good |
| `run.lock` | ✅ Yes* | ✅ Yes | Low | ✅ Good |

\* Append-only or lock file pattern (inherently atomic)

---

## Files Needing Updates

### Critical (HIGH Risk):
1. **`kill_switch.json`** - No atomic write, no locking
2. **`regime_state.json`** - No atomic write, no locking

### Medium Priority:
3. **`positions.json`** - Has atomic write, but missing file locking

---

## Recommendations

1. **Create atomic_file utility module** with:
   - `atomic_write_json()` - Temp file + rename + locking
   - `atomic_read_json()` - File locking during read

2. **Update all state file writes** to use atomic utilities:
   - `kill_switch_manual.py` → Use `atomic_write_json()`
   - `regime_buffer.py` → Use `atomic_write_json()`
   - `positions.py` → Use `atomic_write_json()` (adds locking)

3. **Keep existing implementations** that are already correct:
   - `safety_wrapper.py` - Already perfect
   - `order_wal.py` - Already perfect
   - `run_lock.py` - Already perfect

---

## Next Steps

1. ✅ Create `regimeflex/utils/atomic_file.py`
2. ⏳ Update `kill_switch_manual.py`
3. ⏳ Update `regime_buffer.py`
4. ⏳ Update `positions.py` (add locking)

