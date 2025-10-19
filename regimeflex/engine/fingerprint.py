# engine/fingerprint.py
from __future__ import annotations
from pathlib import Path
import hashlib

CANDIDATE_FILES = [
    "config/run.yaml",
    "config/schedule.yaml",
    "config/data.yaml",
    "config/broker.yaml",
    "config/telemetry.yaml",
    "config/logs.yaml",
    "config/exposure.yaml",
    "config/risk.yaml",
    "config/strategies.yaml",
]

def file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except Exception:
        return b""  # missing files are treated as empty

def compute_fingerprint(root: str = ".") -> dict:
    """Return dict with sha256 hash and the list of files included."""
    rootp = Path(root)
    h = hashlib.sha256()
    included: list[str] = []
    for rel in CANDIDATE_FILES:
        p = rootp / rel
        if p.exists():
            h.update(rel.encode("utf-8") + b"\n")
            h.update(file_bytes(p) + b"\n")
            included.append(rel)
    return {
        "sha256_16": h.hexdigest()[:16],  # short display
        "sha256": h.hexdigest(),
        "files": included,
    }
