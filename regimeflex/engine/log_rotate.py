# engine/log_rotate.py
from __future__ import annotations
from pathlib import Path
from typing import List
from datetime import datetime, timezone, timedelta
import gzip
import shutil
import os
import glob

def _older_than(path: Path, cutoff_ts: float) -> bool:
    try:
        return path.stat().st_mtime < cutoff_ts
    except Exception:
        return False

def _gzip_file(src: Path) -> Path:
    dst = src.with_suffix(src.suffix + ".gz")
    # write to temp then atomically replace
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with src.open("rb") as fin, gzip.open(tmp, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    os.replace(tmp, dst)
    # remove original after successful replace
    src.unlink(missing_ok=True)
    return dst

def rotate_logs(patterns: List[str], days_old: int, exclude_gz: bool = True) -> List[Path]:
    """
    Gzip-compress files older than days_old for the given glob patterns.
    Returns list of rotated (compressed) Paths.
    """
    rotated: List[Path] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
    cutoff_ts = cutoff.timestamp()

    for pat in patterns or []:
        for p in map(Path, glob.glob(pat, recursive=False)):
            if not p.exists() or not p.is_file():
                continue
            if exclude_gz and p.suffix.endswith(".gz"):
                continue
            if _older_than(p, cutoff_ts):
                try:
                    dst = _gzip_file(p)
                    rotated.append(dst)
                except Exception:
                    # best-effort; skip on failure
                    continue
    return rotated

