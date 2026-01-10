#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any


def tail_incidents(day: str | None, limit: int, root: Path) -> Dict[str, Any]:
    """Tail incidents from a specific day's log file."""
    if day is None:
        day = str(datetime.now(timezone.utc).date())

    limit = int(limit)
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200

    path = root / "logs" / "incidents" / f"{day}_incidents.jsonl"
    if not path.exists():
        return {"day": day, "limit": limit, "count": 0, "items": []}

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        items: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue

        # latest first
        items = list(reversed(items))
        return {"day": day, "limit": limit, "count": len(items), "items": items}
    except Exception:
        return {"day": day, "limit": limit, "count": 0, "items": []}


if __name__ == "__main__":
    # Detect if we're at project root or regimeflex directory
    cwd = Path(".")
    if (cwd / "regimeflex" / "config").exists():
        root = cwd / "regimeflex"
    else:
        root = cwd
    
    day = None
    limit = 20
    for arg in sys.argv[1:]:
        if arg.startswith("--day="):
            day = arg.split("=", 1)[1].strip() or None
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=", 1)[1].strip())
            except Exception:
                limit = 20

    print(json.dumps(tail_incidents(day, limit, root), indent=2))

