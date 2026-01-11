"""
Atomic file operations to prevent corruption.

This module provides safe file write/read operations that prevent corruption
if a process crashes mid-write. Uses temp file + atomic rename pattern
with file locking for thread/process safety.

Usage:
    from regimeflex.utils.atomic_file import atomic_write_json, atomic_read_json
    
    # Write JSON atomically
    success = atomic_write_json(Path("data/state/positions.json"), {"TQQQ": 100.0})
    
    # Read JSON atomically
    data = atomic_read_json(Path("data/state/positions.json"), default={})
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Dict

# File locking support (Unix/Linux)
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


def atomic_write_json(
    filepath: Path,
    data: Dict[str, Any],
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    Atomically write JSON data to file.
    
    Uses temp file + rename to prevent corruption if process crashes mid-write.
    Includes file locking for thread/process safety.
    
    Process:
    1. Write to temporary file in same directory
    2. Lock file during write (fcntl.flock)
    3. Flush and sync to disk
    4. Atomically rename temp file to target (os.replace)
    
    Args:
        filepath: Path to JSON file
        data: Dictionary to write
        indent: JSON indentation level (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file in same directory (ensures atomic rename works)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(filepath.parent),
            prefix=f'.{filepath.name}.tmp.',
            suffix='',
            text=True
        )
        
        try:
            # Write JSON to temp file with locking
            with os.fdopen(tmp_fd, 'w') as f:
                if HAS_FCNTL:
                    # Lock file during write (exclusive lock)
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                else:
                    # Windows fallback - no fcntl, just write
                    json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
                    f.flush()
            
            # Atomic rename (replaces old file atomically)
            # On Unix/Linux, rename is atomic. On Windows, may need special handling.
            if os.name == 'nt':  # Windows
                # On Windows, rename may fail if file exists, so delete first
                if filepath.exists():
                    filepath.unlink()
            
            os.replace(tmp_path, filepath)
            return True
            
        except Exception as e:
            # Clean up temp file on error
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except:
                pass
            raise
            
    except Exception as e:
        # Log error but don't raise (caller can check return value)
        import sys
        print(f"Error writing {filepath}: {e}", file=sys.stderr)
        return False


def atomic_read_json(
    filepath: Path,
    default: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Atomically read JSON data from file.
    
    Uses file locking during read to prevent reading partially-written files.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Dictionary from JSON file, or default if file missing/invalid
    """
    if not filepath.exists():
        return default
    
    try:
        with open(filepath, 'r') as f:
            if HAS_FCNTL:
                # Lock file during read (shared lock allows multiple readers)
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                # Windows fallback - no fcntl, just read
                data = json.load(f)
            
            return data
            
    except (json.JSONDecodeError, IOError, OSError) as e:
        # File is corrupted or unreadable
        import sys
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return default
    except Exception as e:
        # Unexpected error
        import sys
        print(f"Unexpected error reading {filepath}: {e}", file=sys.stderr)
        return default


def atomic_delete_file(filepath: Path) -> bool:
    """
    Atomically delete a file.
    
    Args:
        filepath: Path to file to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    except Exception as e:
        import sys
        print(f"Error deleting {filepath}: {e}", file=sys.stderr)
        return False

