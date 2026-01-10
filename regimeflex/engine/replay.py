# engine/replay.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json

def _nowz():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def _df_tail_records(df, n: int):
    if df is None or len(df) == 0:
        return []
    t = df.tail(n).copy()
    # keep only standard OHLCV columns if present
    cols = [c for c in ["date","open","high","low","close","volume"] if c in t.columns]
    if "date" not in cols and t.index.name is not None:
        t = t.reset_index()
        cols = [c for c in ["index","open","high","low","close","volume"] if c in t.columns]
    return [
        {k: (str(v) if k in ("date","index") else float(v)) for k,v in row.items() if k in cols}
        for row in t.to_dict(orient="records")
    ]

def write_replay_bundle(
    out_dir: Path,
    price_common_date: str,
    symbols_data: dict,      # {"QQQ": {"df": long_df, "last_px": x}, "PSQ": {...}}
    context: dict,           # crumbs + selected metrics
    positions_before: dict,
    intents: list,
    positions_after: dict,
    bars_tail: int = 5,
    include_prices: bool = True,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"replay_{price_common_date.replace('-','')}_{datetime.now(timezone.utc).strftime('%H%MZ')}.json"
    path = out_dir / fname

    long_sym = context.get("exec_long") or next(iter(symbols_data.keys()), "") if symbols_data else ""
    short_sym = context.get("exec_short") or (
        next(iter([k for k in symbols_data.keys() if k != long_sym]), "")
        if symbols_data else ""
    )

    payload = {
        "annotation": {
            "summary": f"Replay snapshot for {price_common_date}",
            "intents": len(intents or []),
            "no_op": bool(context.get("no_op", False)),
            "no_op_reason": context.get("no_op_reason", ""),
            "long_sym": long_sym,
            "short_sym": short_sym,
        },
        "ts_utc": _nowz(),
        "as_of": price_common_date,
        "brand": {"name": "RegimeFlex", "config_hash16": context.get("config_hash16","")},
        "symbols": {},
        "state": {
            "positions_before": positions_before or {},
            "positions_after": positions_after or {},
            "intents": intents or [],
        },
        "guards": {
            "session": context.get("session"),
            "session_note": context.get("session_note"),
            "no_op": context.get("no_op", False),
            "no_op_reason": context.get("no_op_reason",""),
            "bar_hygiene": {
                "fail": context.get("bar_hygiene_fail", False),
                "notes": context.get("bar_hygiene_notes", {})
            },
            "asof_check": context.get("price_common_date",""),
            "adv_guard": context.get("adv_guardrail", {}),
            "liquidity_depth": context.get("liquidity_depth", {}),
        },
        "metrics": {
            "signal_stability": context.get("signal_stability", {}),
            "regime_accuracy": context.get("regime_accuracy", {}),
            "exec_quality": context.get("exec_quality", {}),
            "fill_quality_drift": context.get("fill_quality_drift", {}),
            "exposure_concentration": context.get("exposure_concentration", {}),
        },
        "provenance": {
            "config_hash": context.get("config_hash",""),
            "config_hash16": context.get("config_hash16",""),
            "report_sha256": context.get("report_sha256",""),
            "price_source": context.get("price_source",{}),
            "model": context.get("model", {}),
            "execution_mode": context.get("execution_mode", {}),
        }
    }

    if include_prices:
        for sym, obj in (symbols_data or {}).items():
            recs = _df_tail_records(obj.get("df"), bars_tail)
            payload["symbols"][sym] = {
                "last_price": float(obj.get("last_px", 0.0)),
                "bars_tail": recs
            }

    # atomic write
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, path)
    return path

