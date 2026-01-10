# engine/config_echo.py
from __future__ import annotations
from typing import Dict
from .config import Config

def collect_config_echo() -> Dict[str, str | float | int | bool]:
    C = Config(".")
    # execution
    ex = C._load_yaml("config/execution.yaml")
    pair = (ex.get("pair") or "QQQ_PSQ").upper()

    # schedule / EOD guard
    sch = C._load_yaml("config/schedule.yaml")
    eod = (sch.get("eod_guard") or {})
    eod_min = int(eod.get("min_minutes_before_close", 30))
    eod_override = bool(eod.get("allow_early_override", False))

    # risk
    r = C._load_yaml("config/risk.yaml") if (C.root / "config/risk.yaml").exists() else {}
    tov = (r.get("turnover") or {})
    cad = (r.get("cadence") or {})
    ex_thr = (r.get("exposure_threshold") or {})
    coal = (r.get("coalescing") or {})
    tov_max = float(tov.get("max_pct_of_equity", 0.15))
    tov_mode = str(tov.get("mode", "clamp"))
    cad_en = bool(cad.get("enabled", True))
    cad_days = int(cad.get("min_days_between", 1))
    ex_en = bool(ex_thr.get("enabled", True))
    ex_min = float(ex_thr.get("min_delta_abs", 0.01))
    coal_en = bool(coal.get("enabled", True))
    coal_dust = float(coal.get("close_dust_shares", 1.0))

    # data staleness
    d = C._load_yaml("config/data.yaml")
    st = (d.get("staleness") or {})
    stale_days = int(st.get("max_days_ok", 3))

    # metrics
    m = C._load_yaml("config/metrics.yaml") if (C.root / "config/metrics.yaml").exists() else {}
    tsi = (m.get("turnover_stability") or {})
    tsi_win = int(tsi.get("window_days", 7))
    tsi_thr = float(tsi.get("warn_threshold", 0.25))

    # telemetry
    t = C._load_yaml("config/telemetry.yaml")
    tel_en = bool(t.get("enabled", True))
    ping = bool(t.get("decision_ping", True))

    return {
        "pair": pair,
        "eod": f"{eod_min}m{' +OVR' if eod_override else ''}",
        "turnover": f"{tov_mode}≤{tov_max:.0%}",
        "cadence": f"{'on' if cad_en else 'off'}/{cad_days}d",
        "minΔ": f"{ex_min:.0%}" if ex_en else "off",
        "coalesce": f"{'on' if coal_en else 'off'}/dust<{coal_dust}",
        "stale≤": f"{stale_days}d",
        "tsi": f"{tsi_win}d≤{tsi_thr:.0%}",
        "tele": f"{'on' if tel_en else 'off'}{' +ping' if ping and tel_en else ''}",
    }
