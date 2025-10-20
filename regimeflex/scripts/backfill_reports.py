import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.data import load_from_cache
from engine.report import write_daily_html
from engine.exposure import exposure_allocator, classify_phase
from engine.guardrails import enforce_exposure_caps
from engine.symbols import resolve_signal_underlier
from engine.fingerprint import compute_fingerprint

def _to_date(s):
    return None if s in (None, "", "null") else datetime.fromisoformat(s).date()

def main():
    cfg = Config(".")._load_yaml("config/backfill.yaml")
    run = Config(".").run or {}
    equity = float(run.get("equity", 25_000.0))

    out_dir = cfg.get("out_dir", "reports/backfill")
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # resolve signal underlier from cache (falls back to QQQ if NDX missing)
    sig_sym, sig_df_all = resolve_signal_underlier()

    # execution underliers for valuation
    qqq = load_from_cache("QQQ")
    psq = load_from_cache("PSQ")
    if qqq is None or psq is None or qqq.empty or psq.empty:
        raise RuntimeError("QQQ/PSQ cache missing for valuation.")

    # date range
    start = _to_date(cfg.get("start_date"))
    end = _to_date(cfg.get("end_date"))
    if start:
        sig_df_all = sig_df_all[sig_df_all.index.date >= start]
    if end:
        sig_df_all = sig_df_all[sig_df_all.index.date <= end]
    if sig_df_all.empty:
        RF.print_log("No dates in range after filtering.", "ERROR")
        return

    # warm-up length: need at least slow MA; read from exposure.yaml
    exp = Config(".")._load_yaml("config/exposure.yaml")
    slow_ma = int(exp["trend"]["slow_ma"])
    fast_ma = int(exp["trend"]["fast_ma"])
    bb_p = int(exp["weights"]["bb_period"])
    bb_std = float(exp["weights"]["bb_std"])

    fp = compute_fingerprint(".")  # config hash for breadcrumbs
    skip_if_exists = bool(cfg.get("skip_if_exists", True))

    generated = 0
    for d in sig_df_all.index:
        # ensure we have enough history up to date d
        hist = sig_df_all.loc[:d]
        if len(hist) < slow_ma or pd.isna(hist["close"].rolling(slow_ma).mean().iloc[-1]):
            continue

        # allocator and guard
        alloc = exposure_allocator(hist)
        alloc, guard_note = enforce_exposure_caps(alloc)
        phase = classify_phase(hist, fast=fast_ma, bb_p=bb_p, bb_std=bb_std)

        # valuation prices on date d
        if d not in qqq.index or d not in psq.index:
            # if ETF bars missing this date, skip
            continue
        px_qqq = float(qqq.loc[d, "close"])
        px_psq = float(psq.loc[d, "close"])

        # choose side and compute target (no orders; just a report)
        tqqq_w = float(alloc["TQQQ"])
        sqqq_w = float(alloc["SQQQ"])
        if tqqq_w >= sqqq_w:
            symbol = "TQQQ"
            dollars = equity * tqqq_w
            shares = dollars / px_qqq if px_qqq > 0 else 0.0
            direction = "LONG" if dollars > 0 else "FLAT"
        else:
            symbol = "SQQQ"
            dollars = equity * sqqq_w
            shares = dollars / px_psq if px_psq > 0 else 0.0
            direction = "LONG" if dollars > 0 else "FLAT"

        # build a minimal run-like result
        result = {
            "target": {
                "symbol": symbol,
                "direction": direction,
                "dollars": round(dollars, 2),
                "shares": round(shares, 6),
                "notes": "BACKFILL_STUB",
            },
            "positions_before": {},   # not simulated to avoid behavioral assumptions
            "intents": [],            # backfill: no orders
            "positions_after": {},    # backfill: none
            "breadcrumbs": {
                "signal_underlier": sig_sym,
                "phase": phase,
                "config_hash16": fp["sha256_16"],
                "eod_guard": "backfill",
                "plan_reason": f"backfill: phase={phase} caps={guard_note}",
            },
        }

        # output named by the **historical date**
        stamp = d.strftime("%Y-%m-%d")
        fname = f"daily_report_{stamp}.html"
        path = Path(out_dir) / fname
        if skip_if_exists and path.exists():
            continue

        # temporarily adjust writer to force date in filename: we'll emulate by writing then renaming
        # (write_daily_html names by 'now'; we'll just write and overwrite target path)
        tmp_path = write_daily_html(result, out_dir=out_dir, filename_prefix="daily_report")
        Path(tmp_path).rename(path)
        generated += 1

    RF.print_log(f"Backfill produced {generated} reports → {out_dir}", "SUCCESS")

if __name__ == "__main__":
    main()
