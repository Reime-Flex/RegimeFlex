# engine/pnl.py
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import csv
from typing import Dict

from .identity import RegimeFlexIdentity as RF

SNAP_DIR = Path("logs/trading")
SNAP_DIR.mkdir(parents=True, exist_ok=True)
SNAP_CSV = SNAP_DIR / "daily_snapshot.csv"

def _utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _ensure_header(path: Path):
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "date",
            "equity_ref",
            "total_mv",
            "gross_exposure_pct",
            # per-symbol pairs will follow (symbol_mv, symbol_w)
            # we'll keep generic columns for QQQ and PSQ, since that's what we use
            "QQQ_mv","QQQ_w",
            "PSQ_mv","PSQ_w",
        ])

def snapshot_from_positions(positions: Dict[str, float],
                            prices: Dict[str, float],
                            equity_ref: float) -> Dict[str, float]:
    """
    Simple valuation snapshot:
      mv_sym = shares * price (signed long-only since ETFs are long positions)
      total_mv = sum(abs(mv_sym))    # gross
      weights = mv_sym / equity_ref  # as a fraction of reference equity
    """
    mv = {}
    for sym, sh in positions.items():
        if sym in prices:
            mv[sym] = float(sh) * float(prices[sym])
        else:
            mv[sym] = 0.0

    total_gross = sum(abs(v) for v in mv.values())
    gross_exposure_pct = (total_gross / equity_ref) if equity_ref > 0 else 0.0

    # Build row dict for our two core symbols; others default to 0
    qqq_mv = mv.get("QQQ", 0.0)
    psq_mv = mv.get("PSQ", 0.0)
    qqq_w  = qqq_mv / equity_ref if equity_ref > 0 else 0.0
    psq_w  = psq_mv / equity_ref if equity_ref > 0 else 0.0

    # Handle NaN values
    import math
    if math.isnan(qqq_mv):
        qqq_mv = 0.0
    if math.isnan(psq_mv):
        psq_mv = 0.0
    if math.isnan(qqq_w):
        qqq_w = 0.0
    if math.isnan(psq_w):
        psq_w = 0.0
    if math.isnan(gross_exposure_pct):
        gross_exposure_pct = 0.0

    return {
        "date": _utc_date_str(),
        "equity_ref": float(equity_ref),
        "total_mv": float(qqq_mv + psq_mv),     # signed net MV
        "gross_exposure_pct": float(gross_exposure_pct),
        "QQQ_mv": float(qqq_mv),
        "QQQ_w": float(qqq_w),
        "PSQ_mv": float(psq_mv),
        "PSQ_w": float(psq_w),
    }

def append_snapshot_csv(row: Dict[str, float]) -> None:
    _ensure_header(SNAP_CSV)
    with SNAP_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            row["date"],
            f"{row['equity_ref']:.2f}",
            f"{row['total_mv']:.2f}",
            f"{row['gross_exposure_pct']:.4f}",
            f"{row['QQQ_mv']:.2f}",
            f"{row['QQQ_w']:.4f}",
            f"{row['PSQ_mv']:.2f}",
            f"{row['PSQ_w']:.4f}",
        ])
    RF.print_log(f"Snapshot appended → {SNAP_CSV}", "SUCCESS")
