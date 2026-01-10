# engine/incident_view.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any


def load_incidents_for_date(root: str | Path = ".", day: str | None = None) -> List[Dict[str, Any]]:
    """
    Load incidents for a given date (YYYY-MM-DD).
    If day is None, use today's UTC date.
    Returns a list of dicts.
    """
    root = Path(root)
    if day is None:
        day = str(datetime.now(timezone.utc).date())

    fname = root / "logs" / "incidents" / f"{day}_incidents.jsonl"
    if not fname.exists():
        return []

    incidents: List[Dict[str, Any]] = []
    with fname.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                incidents.append(json.loads(line))
            except Exception:
                continue
    return incidents

