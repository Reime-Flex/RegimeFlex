from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict

LEDGER_DIR = Path("logs/audit")
LEDGER_DIR.mkdir(parents=True, exist_ok=True)

def ens_timestamp() -> str:
    """RFC3339 with Zulu (e.g., 2025-10-18T14:03:22Z)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def block_height() -> str:
    """Daily 'block' like a ledger slice."""
    return datetime.now(timezone.utc).strftime("%Y%m%d")

def short_hash(payload: Dict[str, Any]) -> str:
    """Stable 10-char hash over sorted JSON."""
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()[:10]

@dataclass(frozen=True)
class AuditRecord:
    tx_hash: str
    timestamp: str
    block: str
    kind: str            # e.g., "PLAN" | "ORDER" | "FILL"
    data: Dict[str, Any]

class ENSStyleAudit:
    def __init__(self, dirpath: Path = LEDGER_DIR):
        self.dirpath = dirpath

    def _ledger_path(self, block: str) -> Path:
        return self.dirpath / f"ledger_{block}.jsonl"

    def log(self, kind: str, data: Dict[str, Any]) -> AuditRecord:
        ts = ens_timestamp()
        blk = block_height()
        # compute hash over kind + data + block
        payload = {"kind": kind, "block": blk, "timestamp": ts, "data": data}
        h = short_hash(payload)
        rec = AuditRecord(tx_hash=h, timestamp=ts, block=blk, kind=kind, data=data)
        # append JSONL
        with self._ledger_path(blk).open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec
