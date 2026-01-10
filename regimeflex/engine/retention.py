# engine/retention.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple

def _sorted_by_mtime_desc(paths: List[Path]) -> List[Path]:
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)

def prune_reports(reports_dir: Path, entries: List[Tuple[str, int]]) -> List[Path]:
    """
    entries: list of (glob_pattern, max_keep)
    Returns list of deleted file Paths.
    """
    deleted: List[Path] = []
    for pattern, max_keep in entries:
        files = _sorted_by_mtime_desc(list(reports_dir.glob(pattern)))
        if max_keep is None or max_keep < 0:
            continue
        for p in files[max_keep:]:
            try:
                p.unlink(missing_ok=True)
                deleted.append(p)
            except Exception:
                pass
    return deleted

