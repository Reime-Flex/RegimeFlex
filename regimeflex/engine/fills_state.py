# engine/fills_state.py
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone

FILLS_FILE = Path("logs/trading/fills_state.jsonl")

def append_fill_record(symbol: str, side: str, qty: float, status: str, filled_qty: float | None, broker_id: str | None):
    FILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "symbol": symbol,
        "side": side.lower(),   # "buy" or "sell"
        "qty": float(qty),
        "status": status,       # e.g., "accepted", "filled", "partially_filled", "rejected", ...
        "filled_qty": float(filled_qty) if filled_qty is not None else None,
        "broker_id": broker_id,
    }
    with FILLS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
