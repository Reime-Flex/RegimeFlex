# engine/order_preview.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import csv
from typing import List, Dict, Any

def write_order_preview(intents: List[Dict[str, Any]], meta: Dict[str, Any] | None = None,
                        out_dir: Path = Path("reports")) -> Path:
    """
    Dump planned order intents to a CSV for eyeballing when dry_run=true.
    'intents' is your planner's list of OrderIntent-like dicts.
    'meta' may include minutes_to_close, exec pair, price date, etc.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"orders_preview_{ts}.csv"

    # Flatten meta section at top as comment lines for quick context
    with path.open("w", newline="", encoding="utf-8") as f:
        if meta:
            f.write("# meta\n")
            for k, v in meta.items():
                f.write(f"# {k},{v}\n")
            f.write("\n")

        fields = [
            "symbol", "side", "qty", "order_type", "time_in_force",
            "limit_price", "notional_est",
            "reason"
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in intents or []:
            # be defensive about optional keys
            sym = it.get("symbol", "")
            qty = float(it.get("qty", 0.0))
            lim = it.get("limit_price", None)
            px  = float(lim) if lim is not None else float(it.get("mark_price", 0.0))
            w.writerow({
                "symbol": sym,
                "side": it.get("side", ""),
                "qty": round(qty, 6),
                "order_type": it.get("order_type", ""),
                "time_in_force": it.get("time_in_force", ""),
                "limit_price": "" if lim is None else round(float(lim), 6),
                "notional_est": round(qty * (px or 0.0), 2),
                "reason": it.get("reason", ""),
            })
    return path
