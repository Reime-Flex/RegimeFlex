#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def load_latest_replay(root: Path) -> Optional[Dict[str, Any]]:
    """Load the latest replay JSON file."""
    # Check both possible locations for replays
    replays = root / "replays"
    if not replays.exists():
        # Try parent directory if we're in regimeflex
        parent_replays = root.parent / "replays"
        if parent_replays.exists():
            replays = parent_replays
        else:
            return None
    
    files = sorted(replays.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    
    p = files[0]
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        obj["_path"] = str(p)
        return obj
    except Exception:
        return None


def summarize(replay: Dict[str, Any]) -> Dict[str, Any]:
    """Create a safe summary of the replay, excluding large payloads."""
    out: Dict[str, Any] = {
        "path": replay.get("_path"),
        "as_of": replay.get("as_of"),
        "provenance": replay.get("provenance", {}),
        "model": replay.get("model", {}),
        "guards": replay.get("guards", {}),
        "metrics": replay.get("metrics", {}),
        "annotation": replay.get("annotation", {}),
    }
    # Keep crumbs if present, but do not assume structure
    if "breadcrumbs" in replay:
        crumbs = replay.get("breadcrumbs") or {}
        out["breadcrumbs_keys"] = sorted(list(crumbs.keys()))
        # Include a few key breadcrumb fields if they exist
        if "price_source" in crumbs:
            out["breadcrumbs"] = {"price_source": crumbs.get("price_source")}
        if "price_source_check" in crumbs:
            out["breadcrumbs"]["price_source_check"] = crumbs.get("price_source_check")
    return out


if __name__ == "__main__":
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        root = cwd / "regimeflex"
    else:
        root = cwd
    
    mode = "summary"
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1].strip() or "summary"

    r = load_latest_replay(root)
    if not r:
        print(json.dumps({"found": False}, indent=2))
        raise SystemExit(0)

    if mode == "full":
        print(json.dumps({"found": True, "replay": r}, indent=2))
    else:
        print(json.dumps({"found": True, "replay": summarize(r)}, indent=2))

