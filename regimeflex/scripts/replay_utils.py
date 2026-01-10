#!/usr/bin/env python
"""
Replay file utilities for RegimeFlex scripts.

Consolidates replay file loading logic to avoid duplication.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .path_utils import find_replay_directory, detect_project_root


def load_latest_replay(root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load the latest replay JSON file.
    
    This is a consolidated version of the load_latest_replay function
    that was duplicated across multiple scripts.
    
    Args:
        root: Optional root directory. If None, will detect automatically.
              Can be project root or regimeflex root.
    
    Returns:
        Dictionary containing replay data with "_path" key added, or None if not found.
    """
    if root is None:
        project_root, regimeflex_root = detect_project_root()
        # Try regimeflex root first, then project root
        root = regimeflex_root
    
    # Check both possible locations for replays
    replays = root / "replays"
    if not replays.exists():
        # Try parent directory if we're in regimeflex
        parent_replays = root.parent / "replays"
        if parent_replays.exists():
            replays = parent_replays
        else:
            # Try using find_replay_directory as fallback
            replay_dir = find_replay_directory()
            if replay_dir:
                replays = replay_dir
            else:
                return None
    
    # Find all replay files
    files = list(replays.glob("replay_*.json"))
    if not files:
        return None
    
    # Sort by modification time (most recent first)
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Load the latest file
    p = files[0]
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        obj["_path"] = str(p)
        return obj
    except Exception:
        return None


def load_latest_replay_from_dir(replays_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Load the latest replay from a specific directory.
    
    This version is used when the directory is already known.
    
    Args:
        replays_dir: Path to the replays directory.
    
    Returns:
        Dictionary containing replay data with "_path" key added, or None if not found.
    """
    if not replays_dir.exists():
        return None
    
    files = list(replays_dir.glob("replay_*.json"))
    if not files:
        return None
    
    # Sort by modification time (most recent first)
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    p = files[0]
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        obj["_path"] = str(p)
        return obj
    except Exception:
        return None

