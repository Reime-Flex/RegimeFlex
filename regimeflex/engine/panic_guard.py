# engine/panic_guard.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import tempfile
from typing import Dict, Any, List

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def write_panic_bundle(
    out_dir: Path,
    base_filename: str,
    intents: List[Dict[str, Any]],
    crumbs: Dict[str, Any],
    context: Dict[str, Any],
) -> Path:
    """
    Atomically write a panic file capturing intents + essential context.
    Returns the final Path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{Path(base_filename).stem}_{_ts()}.json"
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "intents": intents or [],
        "breadcrumbs": crumbs or {},
        "context": context or {},
    }
    # atomic write
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)  # atomic replace
    return path

