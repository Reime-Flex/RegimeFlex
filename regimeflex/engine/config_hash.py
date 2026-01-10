# engine/config_hash.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import hashlib

INCLUDE_EXT = {".yml", ".yaml"}

def list_config_files(root: Path) -> List[Path]:
    cfg = (root / "config")
    if not cfg.exists():
        return []
    # Stable ordering: depth-first by relative path
    return sorted(
        [p for p in cfg.rglob("*") if p.is_file() and p.suffix.lower() in INCLUDE_EXT],
        key=lambda p: str(p.relative_to(root)).lower()
    )

def file_digest(p: Path) -> str:
    h = hashlib.sha256()
    # include relative path in hash to catch renames/layout changes
    rel = str(p)
    h.update(rel.encode("utf-8"))
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def config_snapshot_hash(root: Path = Path(".")) -> Tuple[str, str, list]:
    """
    Returns (full_sha256, short16, manifest)
    manifest = [(relpath, sha256), ...] in deterministic order
    """
    files = list_config_files(root)
    manifest = []
    roll = hashlib.sha256()
    for p in files:
        rel = str(p.relative_to(root))
        d = file_digest(p)
        manifest.append((rel, d))
        roll.update(rel.encode("utf-8"))
        roll.update(d.encode("utf-8"))
    full = roll.hexdigest()
    short = full[:16]
    return full, short, manifest

