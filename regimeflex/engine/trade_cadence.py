# engine/trade_cadence.py
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone, date
from typing import Dict, Optional

FILLS_FILE = Path("logs/trading/fills_state.jsonl")

def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        # Handle various timestamp formats
        ts_clean = ts.replace("Z", "+00:00")
        # Remove double timezone indicators
        if "+00:00+00:00" in ts_clean:
            ts_clean = ts_clean.replace("+00:00+00:00", "+00:00")
        return datetime.fromisoformat(ts_clean)
    except Exception:
        return None

def last_trade_dates() -> Dict[str, date]:
    """
    Returns {SYMBOL: last_fill_date_utc} using logs/trading/fills_state.jsonl.
    Counts any record with filled_qty>0 as a trade.
    """
    out: Dict[str, date] = {}
    if not FILLS_FILE.exists():
        return out
    with FILLS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            fq = rec.get("filled_qty", None)
            if fq is None:
                continue  # skip non-filled entries
            try:
                if float(fq) <= 0:
                    continue
            except Exception:
                continue
            ts = _parse_ts(str(rec.get("ts","")))
            if not ts: 
                continue
            sym = str(rec.get("symbol","")).upper()
            d = ts.date()
            # keep the most recent
            if sym not in out or d > out[sym]:
                out[sym] = d
    return out

def days_since_trade(symbol: str, today: Optional[date] = None) -> Optional[int]:
    """
    Returns calendar days since last trade for SYMBOL, or None if no prior trade.
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    last_map = last_trade_dates()
    sym = symbol.upper()
    if sym not in last_map:
        return None
    return (today - last_map[sym]).days
