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

# Now execute via the module system (this ensures proper package context)
# This makes Python treat regimeflex as a package, enabling relative imports
if __name__ == "__main__":
    # Execute as module: python -m regimeflex <args...>
    import runpy
    
    # Save original argv (without script name)
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Set up sys.argv for module execution
    # When runpy.run_module executes, it will call __main__.py with these args
    sys.argv = ["regimeflex"] + args
    
    # Execute the module
    try:
        runpy.run_module("regimeflex", run_name="__main__")
    except SystemExit as e:
        sys.exit(e.code if e.code is not None else 0)
    except Exception as e:
        print(f"Error executing RegimeFlex: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

