# engine/metrics.py
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

RUN_SUMS = Path("logs/audit/run_summaries.jsonl")

def _parse_date(s: str):
    # s is the "price_common_date" (YYYY-MM-DD) we stored in run_summaries
    try:
        y, m, d = map(int, s.split("-"))
        return datetime(y, m, d, tzinfo=timezone.utc).date()
    except Exception:
        return None

def load_recent_turnovers(window_days: int) -> List[float]:
    if not RUN_SUMS.exists():
        return []
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=window_days - 1)
    vals: List[float] = []
    with RUN_SUMS.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: 
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            d = _parse_date(str(doc.get("ts","")))
            if d is None or d < cutoff or d > today:
                continue
            try:
                vals.append(float(doc.get("turnover_frac", 0.0)))
            except Exception:
                pass
    return vals

def compute_tsi(window_days: int) -> Dict[str, Any]:
    vec = load_recent_turnovers(window_days)
    n = len(vec)
    avg = sum(vec)/n if n else 0.0
    return {
        "window_days": window_days,
        "count_days": n,
        "avg_turnover": avg,      # fraction of equity per day
    }
