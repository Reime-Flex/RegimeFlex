"""
Execution Run Lock
==================
Prevents concurrent execution of the trading loop to avoid race conditions
and double-sizing positions.
"""
from __future__ import annotations

import fcntl
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .identity import RegimeFlexIdentity as RF


RUN_LOCK_FILE = Path("data/state/run.lock")
LOCK_TIMEOUT_SECONDS = 300  # 5 minutes - consider lock stale after this


def acquire_run_lock(timeout_seconds: int = LOCK_TIMEOUT_SECONDS) -> tuple[bool, Optional[str]]:
    """
    Acquire exclusive lock for run execution.
    
    Uses file locking to prevent concurrent runs. If lock file exists and is stale
    (> timeout_seconds old), it will be cleared and a new lock acquired.
    
    Args:
        timeout_seconds: Maximum age of lock file before considering it stale
        
    Returns:
        Tuple of (success, reason)
        - success: True if lock acquired, False otherwise
        - reason: Human-readable reason for success/failure
    """
    RUN_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Check if lock file exists and is stale
        if RUN_LOCK_FILE.exists():
            try:
                with open(RUN_LOCK_FILE, "r") as f:
                    lines = f.read().strip().split("\n")
                    if len(lines) >= 2:
                        pid = lines[0].strip()
                        timestamp_str = lines[1].strip()
                        try:
                            timestamp = float(timestamp_str)
                            age_seconds = time.time() - timestamp
                            
                            if age_seconds > timeout_seconds:
                                # Stale lock - remove it
                                RF.print_log(
                                    f"🧹 Removing stale run lock (age={age_seconds:.0f}s > {timeout_seconds}s, pid={pid})",
                                    "RISK"
                                )
                                RUN_LOCK_FILE.unlink()
                            else:
                                # Lock is still valid - another run is in progress
                                RF.print_log(
                                    f"⏸️ Another run is in progress (pid={pid}, age={age_seconds:.0f}s)",
                                    "RISK"
                                )
                                return False, f"Concurrent run detected (pid={pid}, age={age_seconds:.0f}s)"
                        except (ValueError, IndexError):
                            # Corrupted lock file - remove it
                            RF.print_log("🧹 Removing corrupted run lock file", "RISK")
                            RUN_LOCK_FILE.unlink()
            except Exception as e:
                RF.print_log(f"Error reading lock file: {e}, removing", "RISK")
                try:
                    RUN_LOCK_FILE.unlink()
                except:
                    pass
        
        # Acquire new lock
        lock_fd = open(RUN_LOCK_FILE, "w")
        
        if hasattr(fcntl, 'LOCK_EX'):
            # Unix/Linux - use fcntl for atomic locking
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Write PID and timestamp
                lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
                lock_fd.flush()
                os.fsync(lock_fd.fileno())  # Force write to disk
                RF.print_log(f"🔒 Run lock acquired (pid={os.getpid()})", "INFO")
                return True, f"Lock acquired (pid={os.getpid()})"
            except (IOError, OSError):
                # Lock is held by another process
                lock_fd.close()
                RF.print_log("⏸️ Run lock held by another process", "RISK")
                return False, "Lock held by another process"
        else:
            # Windows fallback - file-based locking without fcntl
            # Write PID and timestamp
            lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
            lock_fd.flush()
            lock_fd.close()
            RF.print_log(f"🔒 Run lock acquired (pid={os.getpid()}, Windows mode)", "INFO")
            return True, f"Lock acquired (pid={os.getpid()}, Windows mode)"
            
    except Exception as e:
        RF.print_log(f"Failed to acquire run lock: {e}", "ERROR")
        return False, f"Lock acquisition failed: {e}"


def release_run_lock() -> None:
    """
    Release run lock.
    
    Removes the lock file if it belongs to this process.
    """
    try:
        if RUN_LOCK_FILE.exists():
            # Verify lock belongs to this process before removing
            try:
                with open(RUN_LOCK_FILE, "r") as f:
                    lines = f.read().strip().split("\n")
                    if len(lines) >= 1:
                        lock_pid = lines[0].strip()
                        if lock_pid == str(os.getpid()):
                            RUN_LOCK_FILE.unlink()
                            RF.print_log(f"🔓 Run lock released (pid={os.getpid()})", "INFO")
                        else:
                            RF.print_log(
                                f"⚠️ Lock file belongs to different PID ({lock_pid} vs {os.getpid()}), not releasing",
                                "RISK"
                            )
            except Exception as e:
                RF.print_log(f"Error verifying lock ownership: {e}", "RISK")
                # Still try to remove if we can't verify
                try:
                    RUN_LOCK_FILE.unlink()
                    RF.print_log("🔓 Run lock released (ownership verification failed)", "INFO")
                except:
                    pass
    except Exception as e:
        RF.print_log(f"Failed to release run lock: {e}", "ERROR")


def is_run_locked() -> bool:
    """
    Check if a run lock is currently active.
    
    Returns:
        True if lock exists and is not stale, False otherwise
    """
    if not RUN_LOCK_FILE.exists():
        return False
    
    try:
        with open(RUN_LOCK_FILE, "r") as f:
            lines = f.read().strip().split("\n")
            if len(lines) >= 2:
                timestamp_str = lines[1].strip()
                timestamp = float(timestamp_str)
                age_seconds = time.time() - timestamp
                
                # Lock is active if not stale
                return age_seconds <= LOCK_TIMEOUT_SECONDS
    except:
        pass
    
    return False

