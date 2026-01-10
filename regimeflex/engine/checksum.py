# engine/checksum.py
from __future__ import annotations
from pathlib import Path
import hashlib
import glob
from typing import List, Dict

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_sidecar(path: Path, digest: str) -> Path:
    side = path.with_suffix(path.suffix + ".sha256")
    side.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return side

def checksum_new_artifacts(report_dir: Path, patterns: List[str]) -> Dict[str, str]:
    """
    Returns {filename: sha256} for artifacts matching patterns that already exist.
    Always recomputes hash (idempotent).
    """
    out: Dict[str, str] = {}
    for pat in patterns or []:
        for p in map(Path, glob.glob(str(report_dir / pat))):
            if not p.is_file():
                continue
            d = sha256_file(p)
            write_sidecar(p, d)
            out[p.name] = d
    return out

