from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import fcntl

WAL_FILE = Path("data/state/order_wal.jsonl")

@dataclass
class WALEntry:
    id: str
    timestamp: str
    phase: str  # "INTENT" | "SUBMITTED" | "ACKNOWLEDGED" | "FILLED" | "ROLLED_BACK"
    symbol: str
    side: str
    qty: float
    order_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def _append_wal(entry: WALEntry) -> None:
    """Append entry to write-ahead log with file lock."""
    WAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with WAL_FILE.open("a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(asdict(entry)) + "\n")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def log_intent(intent_id: str, symbol: str, side: str, qty: float) -> None:
    """Log order intent BEFORE submission."""
    _append_wal(WALEntry(
        id=intent_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        phase="INTENT",
        symbol=symbol,
        side=side,
        qty=qty
    ))


def log_submitted(intent_id: str, order_id: str) -> None:
    """Log after order submitted to broker."""
    _append_wal(WALEntry(
        id=intent_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        phase="SUBMITTED",
        symbol="",
        side="",
        qty=0,
        order_id=order_id
    ))


def log_acknowledged(intent_id: str, broker_response: Dict[str, Any]) -> None:
    """Log broker acknowledgment."""
    _append_wal(WALEntry(
        id=intent_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        phase="ACKNOWLEDGED",
        symbol="",
        side="",
        qty=0,
        details=broker_response
    ))


def log_filled(intent_id: str, filled_qty: float, fill_price: float) -> None:
    """Log order fill."""
    _append_wal(WALEntry(
        id=intent_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        phase="FILLED",
        symbol="",
        side="",
        qty=filled_qty,
        details={"fill_price": fill_price}
    ))


def get_pending_orders() -> List[WALEntry]:
    """Get orders that were submitted but not confirmed filled."""
    if not WAL_FILE.exists():
        return []
    
    entries: Dict[str, WALEntry] = {}
    with WAL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entry = WALEntry(**data)
                
                # Track latest phase for each order ID
                if entry.phase in ("FILLED", "ROLLED_BACK"):
                    entries.pop(entry.id, None)
                elif entry.phase in ("INTENT", "SUBMITTED", "ACKNOWLEDGED"):
                    entries[entry.id] = entry
            except Exception:
                continue
    
    return list(entries.values())


def reconcile_on_startup() -> Dict[str, Any]:
    """
    Called on startup to check for orphaned orders.
    Returns dict with reconciliation status and any pending orders.
    """
    pending = get_pending_orders()
    
    if not pending:
        return {"status": "clean", "pending_orders": []}
    
    # Flag for manual review
    return {
        "status": "PENDING_ORDERS_FOUND",
        "pending_orders": [asdict(p) for p in pending],
        "action_required": "Check broker dashboard for order status before proceeding"
    }
