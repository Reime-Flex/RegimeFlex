#!/usr/bin/env python
"""
Path utilities for RegimeFlex scripts.

Consolidates common path resolution logic to avoid duplication.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional


def detect_project_root() -> Tuple[Path, Path]:
    """
    Detect the project root and regimeflex root directories.
    
    Returns:
        Tuple of (project_root, regimeflex_root)
        - project_root: The root directory containing regimeflex/
        - regimeflex_root: The regimeflex/ directory itself
    
    Examples:
        If running from project root:
            project_root = Path(".")
            regimeflex_root = Path("regimeflex")
        
        If running from regimeflex directory:
            project_root = Path("..")
            regimeflex_root = Path(".")
    """
    cwd = Path.cwd()
    
    # Check if we're at project root (has regimeflex/config)
    if (cwd / "regimeflex" / "config").exists():
        project_root = cwd
        regimeflex_root = cwd / "regimeflex"
    # Check if parent is project root
    elif (cwd.parent / "regimeflex" / "config").exists():
        project_root = cwd.parent
        regimeflex_root = cwd.parent / "regimeflex"
    else:
        # Fallback: assume current directory
        project_root = cwd
        regimeflex_root = cwd
    
    return project_root, regimeflex_root


def find_replay_directory(project_root: Optional[Path] = None) -> Optional[Path]:
    """
    Find the replay directory, checking multiple possible locations.
    
    Args:
        project_root: Optional project root. If None, will detect automatically.
    
    Returns:
        Path to replay directory if found, None otherwise.
    """
    if project_root is None:
        project_root, _ = detect_project_root()
    
    # Check multiple possible locations
    possible_dirs = [
        project_root / "replays",                    # Project root/replays
        project_root / "regimeflex" / "replays",    # regimeflex/replays
        Path("replays"),                             # Current dir/replays
        Path("regimeflex/replays"),                  # Current dir/regimeflex/replays
    ]
    
    for dir_path in possible_dirs:
        if dir_path.exists() and dir_path.is_dir():
            return dir_path
    
    return None


def find_incidents_file(project_root: Optional[Path] = None) -> Optional[Path]:
    """
    Find the incidents.jsonl file, checking multiple possible locations.
    
    Args:
        project_root: Optional project root. If None, will detect automatically.
    
    Returns:
        Path to incidents.jsonl if found, None otherwise.
    """
    if project_root is None:
        project_root, _ = detect_project_root()
    
    # Check multiple possible locations
    possible_files = [
        project_root / "logs" / "incidents.jsonl",
        project_root / "regimeflex" / "logs" / "incidents.jsonl",
        Path("logs/incidents.jsonl"),
        Path("regimeflex/logs/incidents.jsonl")
    ]
    
    for file_path in possible_files:
        if file_path.exists():
            return file_path
    
    return None

