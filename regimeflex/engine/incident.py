# engine/incident.py
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime


class IncidentLogger:
    def __init__(self, root: str | Path = "."):
        self.root = Path(root)
        self.dir = self.root / "logs" / "incidents"
        self.dir.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, message: str, meta: dict | None = None):
        """
        Append a structured incident to today's .jsonl file

        level: INFO, WARNING, ERROR, CRITICAL
        message: human readable string
        meta: dict containing useful context (optional)
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        record = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": message,
            "meta": meta or {}
        }

        fname = self.dir / f"{datetime.utcnow().date()}_incidents.jsonl"
        with fname.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

