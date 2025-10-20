# engine/report_csv.py
from __future__ import annotations
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

def write_change_report(result: Dict[str, Any], out_dir: Path = Path("reports")) -> Path:
    """Write prev/desired/delta exposures and key metrics to CSV."""
    bc = (result.get("breadcrumbs") or {})
    prev = (bc.get("prev_exposure") or {})
    des  = (bc.get("desired_exposure") or {})
    dlt  = (bc.get("delta_exposure") or {})
    eq   = bc.get("equity_now", 0.0)
    turnover = bc.get("turnover_frac", 0.0)
    note = bc.get("turnover_note", "")
    no_op = bc.get("no_op", False)
    reason = bc.get("no_op_reason", "")
    pos_src = bc.get("positions_source", "")
    pcd = bc.get("price_common_date", "")
    stale = bc.get("price_stale_note", "")

    # Date stamp for filename
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fpath = out_dir / f"changes_{ts}.csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build rows
    rows = []
    sides = sorted(set(prev.keys()) | set(des.keys()) | set(dlt.keys()))
    for s in sides:
        rows.append({
            "symbol": s,
            "prev_weight": round(float(prev.get(s,0.0)),4),
            "desired_weight": round(float(des.get(s,0.0)),4),
            "delta_weight": round(float(dlt.get(s,0.0)),4),
        })

    meta = {
        "equity_now": eq,
        "turnover_frac": turnover,
        "turnover_note": note,
        "no_op": no_op,
        "no_op_reason": reason,
        "positions_source": pos_src,
        "price_common_date": pcd,
        "price_staleness": stale,
    }

    # Write file
    with fpath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol","prev_weight","desired_weight","delta_weight"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        # blank line then meta
        f.write("\n# Meta\n")
        for k,v in meta.items():
            f.write(f"{k},{v}\n")

    return fpath
