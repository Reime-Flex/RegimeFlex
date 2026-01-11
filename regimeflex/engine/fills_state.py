# engine/fills_state.py
from __future__ import annotations
from pathlib import Path
import json
import fcntl
from datetime import datetime, timezone
from regimeflex.engine.symnorm import sym_upper
from regimeflex.config.paths import FILLS_STATE_FILE

# Use absolute path from paths module
FILLS_FILE = FILLS_STATE_FILE

def append_fill_record(symbol: str, side: str, qty: float, status: str, filled_qty: float | None, broker_id: str | None):
    FILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "symbol": sym_upper(symbol),
        "side": side.lower(),   # "buy" or "sell"
        "qty": float(qty),
        "status": status,       # e.g., "accepted", "filled", "partially_filled", "rejected", ...
        "filled_qty": float(filled_qty) if filled_qty is not None else None,
        "broker_id": broker_id,
    }
    with FILLS_FILE.open("a", encoding="utf-8") as f:
        if hasattr(fcntl, 'LOCK_EX'):
            # Unix/Linux - use fcntl for file locking
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(rec) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        else:
            # Windows fallback - no fcntl, just write
            f.write(json.dumps(rec) + "\n")
