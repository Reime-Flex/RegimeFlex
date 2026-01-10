# engine/drift_fill.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
import json

def _parse_utc(ts: str) -> datetime | None:
    try:
        # Expect "YYYY-MM-DDTHH:MM:SS.sssZ"
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def window_avg_bps(rows: List[Dict[str, Any]], limit: int) -> float | None:
    vals = [r.get("slip_bps") for r in rows if isinstance(r.get("slip_bps"), (int, float))]
    vals = vals[-limit:]
    if not vals:
        return None
    return sum(vals) / float(len(vals))

def baseline_avg_bps(rows: List[Dict[str, Any]], days: int, now_utc: datetime | None = None) -> float | None:
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    start = now_utc - timedelta(days=days)
    vals = []
    for r in rows:
        ts = _parse_utc(r.get("ts_utc", ""))
        if not ts:
            continue
        if ts < start or ts > now_utc:
            continue
        v = r.get("slip_bps")
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if not vals:
        return None
    return sum(vals) / float(len(vals))

def assess_drift(rows: List[Dict[str, Any]], baseline_days: int, compare_window: int, worsen_bps: float) -> Tuple[Dict[str, Any], bool]:
    """
    Returns (summary, is_alert)
    summary: {"current_avg": x, "baseline_avg": y, "delta_bps": d, "count_current": n1, "count_baseline": n2}
    """
    curr = window_avg_bps(rows, compare_window)
    base = baseline_avg_bps(rows, baseline_days)
    summary = {
        "current_avg": None if curr is None else round(curr, 2),
        "baseline_avg": None if base is None else round(base, 2),
        "delta_bps": None,
        "count_current": min(compare_window, len(rows)),
        "count_baseline": None
    }
    # count_baseline: recompute quickly
    # (reuse filter)
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    start = now_utc - timedelta(days=baseline_days)
    nb = 0
    for r in rows:
        ts = _parse_utc(r.get("ts_utc", ""))
        if ts and start <= ts <= now_utc and isinstance(r.get("slip_bps"), (int, float)):
            nb += 1
    summary["count_baseline"] = nb

    if curr is None or base is None:
        return summary, False

    delta = curr - base
    summary["delta_bps"] = round(delta, 2)
    return summary, (delta > float(worsen_bps))

