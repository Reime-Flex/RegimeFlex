# engine/run_summary.py
from __future__ import annotations
from pathlib import Path
import json
import fcntl
from typing import Dict, Any
from regimeflex.config.paths import RUN_SUMMARIES_FILE

# Use absolute path from paths module
RUN_SUM_FILE = RUN_SUMMARIES_FILE

def append_run_summary(result: Dict[str, Any]) -> str:
    bc = (result.get("breadcrumbs") or {})
    tgt = (result.get("target") or {})

    doc = {
        "ts": bc.get("price_common_date") or "",     # session date you priced on
        "hash16": bc.get("config_hash16") or "",
        "underlier": bc.get("signal_underlier") or "",
        "phase": bc.get("phase") or "",
        "exec_long": bc.get("exec_long") or "",
        "exec_short": bc.get("exec_short") or "",
        "prev": bc.get("prev_exposure") or {},
        "desired": bc.get("desired_exposure") or {},
        "delta": bc.get("delta_exposure") or {},
        "turnover_frac": bc.get("turnover_frac", 0.0),
        "turnover_note": bc.get("turnover_note") or "",
        "no_op": bc.get("no_op", False),
        "no_op_reason": bc.get("no_op_reason") or "",
        "equity_now": bc.get("equity_now", 0.0),
        "positions_source": bc.get("positions_source") or "",
        "price_stale": bc.get("price_stale", False),
        "price_staleness_days": bc.get("price_staleness_days", 0),
        "run_duration_sec": bc.get("run_duration_sec", 0.0),
        "target_symbol": tgt.get("symbol") or "",
        "target_direction": tgt.get("direction") or "",
        "target_dollars": tgt.get("dollars", 0.0),
        "target_shares": tgt.get("shares", 0.0),
    }

    RUN_SUM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RUN_SUM_FILE.open("a", encoding="utf-8") as f:
        if hasattr(fcntl, 'LOCK_EX'):
            # Unix/Linux - use fcntl for file locking
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(doc) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        else:
            # Windows fallback - no fcntl, just write
            f.write(json.dumps(doc) + "\n")
    return str(RUN_SUM_FILE)
