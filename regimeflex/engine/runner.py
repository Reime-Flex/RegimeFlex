from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
from typing import Dict, List

from .identity import RegimeFlexIdentity as RF
from .env import load_env
from .config import Config
from .killswitch import is_killed
from .logrotate import rotate_all
from .log_rotate import rotate_logs
from .pnl import snapshot_from_positions, append_snapshot_csv
from .exposure import exposure_allocator, classify_phase
from .guardrails import enforce_exposure_caps
import time
from .versioning import runtime_versions
from .exposure_delta import current_exposure_weights, exposure_delta
from .exposure_reason import compute_exposure_diagnostics, format_plan_reason
from .symbols import resolve_signal_underlier
from .signals import trend_signal, mr_signal, detect_regime, RegimeState
from .instruments import resolve_execution_pair
from .turnover import enforce_turnover_cap
from .reconcile_positions import effective_positions_before
from .report_csv import write_change_report
from .run_summary import append_run_summary
from .order_preview import write_order_preview
from .trade_cadence import days_since_trade
from .metrics import compute_tsi
from .plan_coalesce import coalesce_side_flip
from .symnorm import sym_upper, map_keys_upper, ensure_keys_upper
from .timing import eod_ready
from .fingerprint import compute_fingerprint
from .config_hash import config_snapshot_hash
from .telemetry import Notifier, TGCreds
from .data import get_daily_bars, build_source_meta
from .bar_hygiene import validate_last_bar
from .model_manifest import load_model_manifest
from .stability import flip_count, stability_score
from .regime_accuracy import build_proxy_labels, shift_for_lookahead, accuracy_score
from .concentration import side_concentration, symbol_peak, badge
from .liquidity import rolling_adv, assess_depth
from .adv_guard import enforce_adv_cap
from .replay import write_replay_bundle
from .risk import RiskConfig
from .config_echo import collect_config_echo
from .sanity import check_mutual_exclusive, clamp_smaller_side
from .drift import compute_position_drift
from .kill_switch import evaluate_kill_switch
from .anomaly import detect_anomalies
from .price_source_check import check_price_source
from .harmonize import harmonize_exposure
from .panic_guard import write_panic_bundle
from .env_watchdog import env_guard
from .session_guard import session_status
from .portfolio import compute_target_exposure, TargetExposure
from .exec_planner import plan_orders, OrderIntent
from .exec_alpaca import AlpacaCreds, AlpacaExecutor, ALPACA_PAPER_URL, ALPACA_LIVE_URL, dry_run_details
from .incident import IncidentLogger
from .window_gate import morning_rush_check
from .liquidity import check_zscore_liquidity
from .decay import log_volatility_decay
from .reconcile import compare_intents_vs_orders
from .positions import load_positions, save_positions
from .fills import simulate_fills, apply_simulated_fills, append_fill, load_fills
from .exec_quality import slippage_bps, rolling_stats
from .drift_fill import load_jsonl, assess_drift
from .storage import ENSStyleAudit
from .calendar import is_fomc_blackout, is_opex
from datetime import date
import pandas as pd

def _last_common_close(long_df: pd.DataFrame, short_df: pd.DataFrame) -> tuple:
    """Find the latest common date and prices for both dataframes."""
    # Normalize timestamps to avoid timezone comparison issues
    long_dates_norm = set(long_df.index.tz_localize(None) if long_df.index.tz is not None else long_df.index)
    short_dates_norm = set(short_df.index.tz_localize(None) if short_df.index.tz is not None else short_df.index)
    common_dates_norm = long_dates_norm.intersection(short_dates_norm)
    
    if common_dates_norm:
        # Get the latest common date
        latest_common_date_norm = max(common_dates_norm)
        # Find the original timestamp in the dataframe
        latest_common_date = None
        for idx in long_df.index:
            if (idx.tz_localize(None) if idx.tz is not None else idx) == latest_common_date_norm:
                latest_common_date = idx
                break
        
        long_price = float(long_df.loc[latest_common_date, "close"])
        short_price = float(short_df.loc[latest_common_date, "close"])
    else:
        # Fall back to latest available date for each symbol
        latest_long_date_norm = max(long_dates_norm)
        latest_short_date_norm = max(short_dates_norm)
        latest_common_date_norm = max(latest_long_date_norm, latest_short_date_norm)
        
        # Find original timestamps
        latest_long_date = None
        latest_short_date = None
        for idx in long_df.index:
            if (idx.tz_localize(None) if idx.tz is not None else idx) == latest_long_date_norm:
                latest_long_date = idx
                break
        for idx in short_df.index:
            if (idx.tz_localize(None) if idx.tz is not None else idx) == latest_short_date_norm:
                latest_short_date = idx
                break
        
        # Use the latest available price for each symbol
        long_price = float(long_df.loc[latest_long_date, "close"])
        short_price = float(short_df.loc[latest_short_date, "close"])
        latest_common_date = latest_common_date_norm
    
    return latest_common_date, long_price, short_price

def _intent_to_dict(it: OrderIntent) -> dict:
    return {
        "symbol": it.symbol,
        "side": it.side,
        "qty": round(float(it.qty), 6),
        "order_type": it.order_type,
        "time_in_force": it.time_in_force,
        "limit_price": None if it.limit_price is None else float(it.limit_price),
        "reason": it.reason,
    }

def run_daily_offline(equity: float, vix: float, minutes_to_close: int, min_trade_value: float = 200.0) -> Dict[str, any]:
    t0 = time.perf_counter()
    RF.print_log("RegimeFlex offline daily cycle starting", "INFO")
    
    # Priority 1: Execution Run Lock - Prevent concurrent execution
    from .run_lock import acquire_run_lock, release_run_lock, is_run_locked
    from .kill_switch_manual import is_kill_switch_active
    
    # Check kill switch FIRST (before acquiring lock)
    kill_data = is_kill_switch_active()
    if kill_data:
        RF.print_log(f"⛔ KILL SWITCH ACTIVE: {kill_data.get('reason', 'Unknown')}", "ERROR")
        return {
            "target": {"symbol": "CASH", "direction": "FLAT", "dollars": 0.0, "shares": 0.0},
            "positions_before": load_positions(),
            "intents": [],
            "positions_after": load_positions(),
            "breadcrumbs": {
                "no_op": True,
                "no_op_reason": "KILL_SWITCH",
                "kill_reason": kill_data.get("reason", "Unknown"),
                "kill_activated_at": kill_data.get("activated_at", "Unknown"),
                "config_hash16": cfg_short if 'cfg_short' in locals() else "",
                "run_duration_sec": round(time.perf_counter() - t0, 3)
            },
            "config_fingerprint": fp if 'fp' in locals() else {}
        }
    
    # Acquire run lock
    lock_acquired, lock_reason = acquire_run_lock()
    if not lock_acquired:
        RF.print_log(f"⏸️ Run blocked by lock: {lock_reason}", "RISK")
        return {
            "target": {"symbol": "CASH", "direction": "FLAT", "dollars": 0.0, "shares": 0.0},
            "positions_before": load_positions(),
            "intents": [],
            "positions_after": load_positions(),
            "breadcrumbs": {
                "no_op": True,
                "no_op_reason": "CONCURRENT_RUN",
                "lock_reason": lock_reason,
                "config_hash16": cfg_short if 'cfg_short' in locals() else "",
                "run_duration_sec": round(time.perf_counter() - t0, 3)
            },
            "config_fingerprint": fp if 'fp' in locals() else {}
        }
    
    try:
    
    # Initialize incident logger
    incidents = IncidentLogger(root=".")
    
    # Config echo - one concise sanity line
    echo = collect_config_echo()
    RF.print_log(
        "CFG → "
        f"pair={echo['pair']} | eod={echo['eod']} | turnover={echo['turnover']} | "
        f"cadence={echo['cadence']} | minΔ={echo['minΔ']} | coalesce={echo['coalesce']} | "
        f"stale≤{echo['stale≤']} | tsi={echo['tsi']} | tele={echo['tele']}",
        "INFO"
    )
    
    # Track no-op reason for days with zero intents
    noop_reason = None

    # Config snapshot hash (all YAML files in config/)
    cfg_full, cfg_short, cfg_manifest = config_snapshot_hash(Path("."))
    RF.print_log(f"CFG hash: {cfg_short}", "INFO")

    # Config fingerprint (legacy, for backward compatibility)
    fp = compute_fingerprint(".")
    RF.print_log(f"Config fingerprint: {fp['sha256_16']} ({len(fp['files'])} files)", "INFO")

    # Audit the fingerprint
    audit = ENSStyleAudit()
    audit.log(kind="CFG", data={"hash16": fp["sha256_16"], "hash": fp["sha256"], "files": fp["files"]})
    
    # Note: Kill switch already checked at function start, skip duplicate check

    # EOD timing guard
    ok_time, why = eod_ready(minutes_to_close)
    RF.print_log(f"EOD timing check → {why}", "RISK" if not ok_time else "INFO")
    if not ok_time:
        # Exit cleanly before any actions
        noop_reason = "EOD_GUARD_TOO_EARLY"
        duration_sec = round(time.perf_counter() - t0, 3)
        vers = runtime_versions()
        result = {
            "target": {"symbol": "NA", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "EOD_GUARD"},
            "positions_before": load_positions(),   # optional: show current
            "intents": [],
            "positions_after": load_positions(),
            "breadcrumbs": attach_model_manifest({
                "no_op": True, 
                "no_op_reason": noop_reason, 
                "eod_guard": why, 
                "config_hash16": cfg_short,
                "run_duration_sec": duration_sec,
                "versions": vers,
            }),
            "snapshot": {},
            "config_fingerprint": fp
        }
        
        # Export CSV change report for early exit
        try:
            csv_path = write_change_report(result)
            RF.print_log(f"CSV change report saved → {csv_path}", "INFO")
        except Exception as e:
            RF.print_log(f"CSV export failed: {e}", "ERROR")
            
        # Append run summary JSONL for early exit
        try:
            path = append_run_summary(result)
            RF.print_log(f"Run summary appended → {path}", "INFO")
        except Exception as e:
            RF.print_log(f"Run summary append failed: {e}", "ERROR")
        
        release_run_lock()
        return result

    # Decision window ping (when within EOD window)
    tele_cfg = (Config(".").telemetry or {})
    if tele_cfg.get("decision_ping", True) and tele_cfg.get("enabled", True):
        # brief context
        exp_cfg = Config(".")._load_yaml("config/exposure.yaml")
        fast = exp_cfg["trend"]["fast_ma"]
        bb_p  = exp_cfg["weights"]["bb_period"]
        bb_sd = exp_cfg["weights"]["bb_std"]
        # Use any breadcrumbs already computed (if not yet available, we'll fill what we have)
        phase_txt = locals().get("phase", "") or "N/A"
        underlier_txt = locals().get("sig_sym", "") or "N/A"

        msg = (
            f"*⏰ RegimeFlex Decision Window*\n"
            f"Within EOD window — `{minutes_to_close}m` to close.\n"
            f"*Underlier*: `{underlier_txt}`   *Phase*: `{phase_txt}`\n"
            f"*BB*: {bb_p}/{bb_sd}σ   *FastMA*: {fast}\n"
            f"_This is an informational ping; no orders placed yet._"
        )
        env = load_env()
        notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
        notifier.send(msg)

    # Always print a concise console line too
    RF.print_log(f"Decision window active — {minutes_to_close}m to close", "INFO")

    # Load env + config (keys not required in offline)
    env = load_env()
    cfg = Config(".")
    risk_cfg = RiskConfig()

    # Helper function to attach model manifest to crumbs
    def attach_model_manifest(crumbs_dict: dict) -> dict:
        """Attach model manifest info to breadcrumbs dictionary."""
        manifest = load_model_manifest(Path("."))
        model_info = (manifest.get("model") or {})
        crumbs_dict.update({
            "model": {
                "name": model_info.get("name", "RegimeFlex"),
                "version": model_info.get("version", "0.0.0"),
                "description": model_info.get("description", ""),
                "tags": model_info.get("tags", []),
            }
        })
        return crumbs_dict

    # Calendar guard
    sched = cfg.schedule or {}
    today = date.today()

    is_fomc = is_fomc_blackout(
        today,
        fomc_meetings=sched.get("fomc_dates", []),
        window=tuple(sched.get("fomc_blackout_window", [-1, 1]))
    )
    is_opex_day = is_opex(today, overrides=sched.get("opex_overrides", []))

    # log status
    RF.print_log(f"Calendar → FOMC blackout={is_fomc}, OPEX={is_opex_day}", "RISK")

    # Market session guard
    sch_cfg = Config(".")._load_yaml("config/schedule.yaml")
    ms = (sch_cfg.get("market_session") or {})
    block_full = bool(ms.get("block_full_holidays", True))
    block_half = bool(ms.get("block_half_days", True))

    sess, note = session_status()  # "FULL" | "NO_SESSION" | "HALF_DAY"
    
    # Initialize crumbs early for session guard
    crumbs = {
        "vix": vix,
        "fomc_blackout": is_fomc,
        "opex": is_opex_day,
        "session": sess,
        "session_note": note,
        "config_hash": cfg_full,
        "config_hash16": cfg_short,
        "config_manifest": cfg_manifest,
    }
    
    # Load positions early for early return if needed
    positions_before_early = load_positions()
    
    if sess == "NO_SESSION" and block_full:
        RF.print_log(f"Session guard: {sess} ({note}) → skip trading", "RISK")
        crumbs.update({
            "no_op": True, 
            "no_op_reason": "NO_SESSION",
            "config_hash16": cfg_short,
            "run_duration_sec": round(time.perf_counter() - t0, 3),
            "versions": runtime_versions(),
        })
        attach_model_manifest(crumbs)
        # Store execution mode
        exec_mode = dry_run_details(".")
        crumbs["execution_mode"] = exec_mode
        # Log dry-run if forced by ENV
        if exec_mode.get("dry_run") and exec_mode.get("source") == "env":
            incidents.log(
                "INFO",
                "Run executed in DRY-RUN mode due to environment variable",
                {"env": exec_mode}
            )
        # Build a CASH target and exit early (observability only)
        result = {
            "target": {"symbol":"CASH","direction":"FLAT","dollars":0.0,"shares":0.0,"notes":"market_closed"},
            "positions_before": positions_before_early,
            "intents": [],
            "positions_after": positions_before_early,
            "breadcrumbs": crumbs,
            "config_fingerprint": fp
        }
        
        # Export CSV change report for early exit
        try:
            csv_path = write_change_report(result)
            RF.print_log(f"CSV change report saved → {csv_path}", "INFO")
        except Exception as e:
            RF.print_log(f"CSV export failed: {e}", "ERROR")
            
        # Append run summary JSONL for early exit
        try:
            path = append_run_summary(result)
            RF.print_log(f"Run summary appended → {path}", "INFO")
        except Exception as e:
            RF.print_log(f"Run summary append failed: {e}", "ERROR")
        
        # --- Daily heartbeat telemetry (session guard path) ---
        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
        hb = (tel_cfg.get("heartbeat") or {})
        if bool(hb.get("enabled", True)) and tel_cfg.get("enabled", True):
            try:
                env = load_env()
                notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
                notifier.send_heartbeat(result["breadcrumbs"])
                RF.print_log("Heartbeat sent.", "SUCCESS")
            except Exception as e:
                RF.print_log(f"Heartbeat failed: {e}", "ERROR")
        
        # Optional: stdout heartbeat (always log, even if Telegram disabled)
        bc = result["breadcrumbs"]
        RF.print_log(
            f"HB | {bc.get('config_hash16','??')} · {bc.get('price_common_date','????-??-??')} · "
            f"{bc.get('exec_long','')}/{bc.get('exec_short','')} · {bc.get('run_duration_sec',0):.2f}s · "
            f"{'no-op '+str(bc.get('no_op_reason','')) if bc.get('no_op') else 'active'}",
            "INFO"
        )
        
        return result

    # --- Morning Rush Filter ---
    # Avoid trading 9:30-9:45 AM EST due to opening gap volatility.
    mr_check = morning_rush_check(sch_cfg)
    if mr_check.get("blocked"):
        RF.print_log(f"Morning Rush: {mr_check['reason']}", "RISK")
        crumbs.update({
             "no_op": True,
             "no_op_reason": "MORNING_RUSH",
             "morning_rush_active": True,
             "config_hash16": cfg_short,
             "run_duration_sec": round(time.perf_counter() - t0, 3),
             "versions": runtime_versions()
        })
        attach_model_manifest(crumbs)
        
        result = {
            "target": {"symbol": "CASH", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "morning_rush_wait"},
            "positions_before": positions_before_early,
            "intents": [],
            "positions_after": positions_before_early,
            "breadcrumbs": crumbs,
            "config_fingerprint": fp
        }
        
        # Log via incidents (transient)
        incidents.log("INFO", f"Morning Rush Guard: {mr_check['reason']}", {"now": mr_check["now"]})
        
        # Send heartbeat to notify "Waiting for Morning Rush to clear..."
        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml")
        if bool(tel_cfg.get("enabled", True)):
             try:
                 env = load_env()
                 notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
                 notifier.send_heartbeat(crumbs)
             except Exception:
                 pass
        
        release_run_lock()
        return result

    if sess == "HALF_DAY" and block_half:
        RF.print_log(f"Session guard: {sess} ({note}) → skip trading", "RISK")
        crumbs.update({
            "no_op": True, 
            "no_op_reason": "HALF_DAY",
            "config_hash16": cfg_short,
            "run_duration_sec": round(time.perf_counter() - t0, 3),
            "versions": runtime_versions(),
        })
        attach_model_manifest(crumbs)
        # Store execution mode
        exec_mode = dry_run_details(".")
        crumbs["execution_mode"] = exec_mode
        # Log dry-run if forced by ENV
        if exec_mode.get("dry_run") and exec_mode.get("source") == "env":
            incidents.log(
                "INFO",
                "Run executed in DRY-RUN mode due to environment variable",
                {"env": exec_mode}
            )
        result = {
            "target": {"symbol":"CASH","direction":"FLAT","dollars":0.0,"shares":0.0,"notes":"early_close_block"},
            "positions_before": positions_before_early,
            "intents": [],
            "positions_after": positions_before_early,
            "breadcrumbs": crumbs,
            "config_fingerprint": fp
        }
        
        # Export CSV change report for early exit
        try:
            csv_path = write_change_report(result)
            RF.print_log(f"CSV change report saved → {csv_path}", "INFO")
        except Exception as e:
            RF.print_log(f"CSV export failed: {e}", "ERROR")
            
        # Append run summary JSONL for early exit
        try:
            path = append_run_summary(result)
            RF.print_log(f"Run summary appended → {path}", "INFO")
        except Exception as e:
            RF.print_log(f"Run summary append failed: {e}", "ERROR")
        
        # --- Daily heartbeat telemetry (session guard path) ---
        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
        hb = (tel_cfg.get("heartbeat") or {})
        if bool(hb.get("enabled", True)) and tel_cfg.get("enabled", True):
            try:
                env = load_env()
                notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
                notifier.send_heartbeat(result["breadcrumbs"])
                RF.print_log("Heartbeat sent.", "SUCCESS")
            except Exception as e:
                RF.print_log(f"Heartbeat failed: {e}", "ERROR")
        
        # Optional: stdout heartbeat (always log, even if Telegram disabled)
        bc = result["breadcrumbs"]
        RF.print_log(
            f"HB | {bc.get('config_hash16','??')} · {bc.get('price_common_date','????-??-??')} · "
            f"{bc.get('exec_long','')}/{bc.get('exec_short','')} · {bc.get('run_duration_sec',0):.2f}s · "
            f"{'no-op '+str(bc.get('no_op_reason','')) if bc.get('no_op') else 'active'}",
            "INFO"
        )
        
        return result

    # Resolve execution instruments
    exec_map = resolve_execution_pair()
    LONG  = sym_upper(exec_map["long"])       # "QQQ" or "TQQQ"
    SHORT = sym_upper(exec_map["short"])      # "PSQ" or "SQQQ"
    sides = [LONG, SHORT]

    # Load price refs for sizing/valuations
    long_df  = get_daily_bars(exec_map["long_ref"])
    short_df = get_daily_bars(exec_map["short_ref"])

    # Price source echo & as-of alignment check
    data_cfg = Config(".")._load_yaml("config/data.yaml")
    se = (data_cfg.get("source_echo") or {})
    echo_enabled = bool(se.get("enabled", True))
    strict_same = bool(se.get("strict_same_asof", True))
    tz_hint = str(se.get("timezone_hint", "US/Eastern"))
    
    # Determine provider name
    provider_name = (data_cfg.get("provider") or "cache").lower()
    if provider_name == "cache":
        provider_name = "local-cache"

    if echo_enabled:
        # Build per-symbol metadata
        long_meta  = build_source_meta(LONG,  provider=provider_name, df=long_df)
        short_meta = build_source_meta(SHORT, provider=provider_name, df=short_df)

        # Common as-of (used elsewhere already)
        asof_long  = long_meta["as_of"]
        asof_short = short_meta["as_of"]

        # Stash in breadcrumbs
        crumbs.update({
            "price_source": {
                LONG:  long_meta,
                SHORT: short_meta,
                "tz_hint": tz_hint,
            }
        })

        # Enforce alignment
        if strict_same and asof_long != asof_short:
            RF.print_log(f"Price as-of mismatch: {LONG}={asof_long} vs {SHORT}={asof_short}", "ERROR")
            crumbs.update({"no_op": True, "no_op_reason": "ASOF_MISMATCH"})
            raise RuntimeError(f"ASOF mismatch: {LONG} {asof_long} vs {SHORT} {asof_short}")
        else:
            if asof_long == asof_short:
                crumbs.update({"price_common_date": asof_long})
            else:
                crumbs.update({"price_common_date": f"{asof_long}|{asof_short}"})
            RF.print_log(f"Price as-of: {crumbs['price_common_date']} ({tz_hint})", "INFO")

    # Bar hygiene validation
    bh = (data_cfg.get("bar_hygiene") or {})
    bh_enabled = bool(bh.get("enabled", True))
    bh_action = str(bh.get("action", "quarantine")).lower()

    bad_syms = []
    bad_notes = {}

    if bh_enabled:
        for sym, df in ((LONG, long_df), (SHORT, short_df)):
            ok, note = validate_last_bar(sym, df, bh)
            if not ok:
                bad_syms.append(sym)
                bad_notes[sym] = note

    if bad_syms:
        # expose in breadcrumbs
        crumbs.update({"bar_hygiene_fail": True, "bar_hygiene_notes": bad_notes, "bar_hygiene_action": bh_action})
        RF.print_log(f"Bar hygiene FAIL: {bad_notes}", "ERROR")

        if bh_action == "drop_last":
            # Attempt to drop last bad row(s) and continue
            if LONG in bad_syms and len(long_df) > 0:
                long_df = long_df.iloc[:-1]
            if SHORT in bad_syms and len(short_df) > 0:
                short_df = short_df.iloc[:-1]
            RF.print_log("Bar hygiene: dropped last row for bad symbols; continuing.", "RISK")
        else:
            # quarantine: skip trading today
            crumbs.update({"no_op": True, "no_op_reason": "BAR_HYGIENE"})
            positions_before_early = load_positions()
            result = {
                "target": {"symbol": "CASH", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "bar_hygiene_quarantine"},
                "positions_before": positions_before_early,
                "intents": [],
                "positions_after": positions_before_early,
                "breadcrumbs": crumbs,
            }
            return result
    else:
        crumbs.update({"bar_hygiene_fail": False})

    # Signal underlier
    sig_sym, sig_df_orig = resolve_signal_underlier()
    sig_df = sig_df_orig.copy()
    if "regime_live" not in sig_df.columns:
        slow_ma_series = sig_df["close"].rolling(200, min_periods=200).mean()
        sig_df["regime_live"] = (sig_df["close"] >= slow_ma_series).fillna(False)

    # Compute market phase
    exp_cfg = Config(".")._load_yaml("config/exposure.yaml")
    fast = exp_cfg["trend"]["fast_ma"]
    bb_p = exp_cfg["weights"]["bb_period"]
    bb_std = exp_cfg["weights"]["bb_std"]

    phase = classify_phase(sig_df, fast=fast, bb_p=bb_p, bb_std=bb_std)
    RF.print_log(f"Signal phase → {phase}", "INFO")

    # Signal stability computation
    metrics_cfg = Config(".")._load_yaml("config/metrics.yaml")
    ss_cfg = (metrics_cfg.get("signal_stability") or {})
    ss_enabled = bool(ss_cfg.get("enabled", True))
    ss_lookback = int(ss_cfg.get("lookback_days", 14))
    ss_engines = [str(x) for x in (ss_cfg.get("engines") or ["trend", "mr"])]

    stability = {}
    if ss_enabled and len(sig_df) > 0:
        # Compute signals for last N days
        tail_len = min(ss_lookback, len(sig_df))
        trend_dirs = []
        mr_dirs = []
        
        for i in range(max(0, len(sig_df) - tail_len), len(sig_df)):
            hist_df = sig_df.iloc[:i+1]
            if len(hist_df) < 20:  # need minimum data for signals
                continue
            
            # Detect regime
            regime = detect_regime(hist_df["close"])
            regime = RegimeState(bull=regime.bull, vix=vix, qqq_rvol_20=regime.qqq_rvol_20)
            
            # Trend signal
            t_sig = trend_signal(hist_df, regime, vix_max=30.0, qqq_vol_50d_max=0.40)
            trend_dir = "LONG" if (t_sig.entry and not t_sig.exit) else "FLAT"
            trend_dirs.append(trend_dir)
            
            # MR signal (use QQQ for bull, PSQ for bear)
            active_df = long_df if regime.bull else short_df
            # Align dates: find the date in active_df that matches hist_df's last date
            hist_date = hist_df.index[-1]
            # Find matching date in active_df
            matching_dates = active_df.index[active_df.index <= hist_date]
            if len(matching_dates) > 0:
                active_hist = active_df.loc[:matching_dates[-1]]
                if len(active_hist) >= 20:
                    m_sig = mr_signal(active_hist, regime, z_len=20, vol_confirm_mult=1.2)
                    mr_dirs.append(m_sig.direction)
                else:
                    mr_dirs.append("FLAT")
            else:
                mr_dirs.append("FLAT")
        
        # Compute stability for each engine
        for eng in ss_engines:
            if eng == "trend":
                dirs = trend_dirs
            elif eng == "mr":
                dirs = mr_dirs
            else:
                stability[eng] = {"flips": None, "score": None, "n": 0, "note": "unknown_engine"}
                continue
            
            if len(dirs) > 0:
                flips = flip_count(dirs)
                score = stability_score(dirs, max(1, len(dirs)))
                stability[eng] = {"flips": int(flips), "score": round(score, 3), "n": int(len(dirs))}
            else:
                stability[eng] = {"flips": None, "score": None, "n": 0, "note": "insufficient_data"}
    else:
        if not ss_enabled:
            stability = {"note": "disabled"}
        else:
            stability = {"note": "no_data"}

    # breadcrumbs
    crumbs.update({"signal_stability": stability})

    # Regime accuracy tracker
    ra_cfg = (metrics_cfg.get("regime_accuracy") or {})
    regime_acc = {}
    if bool(ra_cfg.get("enabled", True)):
        min_hist = int(ra_cfg.get("min_history", 60))
        if len(sig_df) >= min_hist:
            lookahead = int(ra_cfg.get("lookahead_days", 5))
            proxy_cfg = ra_cfg.get("proxy", {}) or {}
            vol_win = int(proxy_cfg.get("vol_window", 20))
            high_vol_thr = float(proxy_cfg.get("high_vol_threshold", 0.35))

            price = long_df[["close"]].copy()
            price = price[~price["close"].isna()]
            px = price.reindex(sig_df.index).ffill()

            proxy_bull = build_proxy_labels(px, vol_win=vol_win, high_vol_thr=high_vol_thr)
            proxy_for_scoring = shift_for_lookahead(proxy_bull, lookahead_days=lookahead)

            if "regime_live" in sig_df.columns:
                live = sig_df["regime_live"].astype("boolean")
                acc, cm = accuracy_score(live, proxy_for_scoring)
                acc_val = None if (acc != acc) else round(float(acc), 3)  # NaN-safe
                regime_acc = {
                    "lookahead_days": lookahead,
                    "acc": acc_val,
                    "cm": cm,
                    "vol_window": vol_win,
                    "high_vol_thr": high_vol_thr,
                }
            else:
                regime_acc = {
                    "note": "missing_regime_live",
                    "lookahead_days": lookahead,
                }
        else:
            regime_acc = {"note": "insufficient_history", "available": len(sig_df)}
    else:
        regime_acc = {"note": "disabled"}

    crumbs.update({"regime_accuracy": regime_acc})

    # Allocation from signal underlier
    alloc_raw = exposure_allocator(sig_df)
    alloc_raw, guard_note = enforce_exposure_caps(alloc_raw)
    
    # Remap allocator output to execution symbols
    alloc = {
        LONG:  float(alloc_raw.get("TQQQ", 0.0)),
        SHORT: float(alloc_raw.get("SQQQ", 0.0)),
    }
    # Normalize symbol casing
    alloc = ensure_keys_upper(alloc, sides)
    
    RF.print_log(f"Allocation (guarded) → {LONG}={alloc[LONG]:.2f} {SHORT}={alloc[SHORT]:.2f}", "INFO")

    # Priority 2: Apply Leverage Decay Adjustment to allocation weights
    # Calculate decay_stats early so we can apply adjustment before target creation
    decay_stats = {}
    try:
        from .decay import log_volatility_decay
        # Check Long Side (TQQQ) vs Index (QQQ)
        if long_df is not None and not long_df.empty and sig_df is not None and not sig_df.empty:
            d_long = log_volatility_decay(
                LONG, long_df, sig_sym, sig_df,
                leverage=3.0,
                save_daily=True,
                lookback=20
            )
            decay_stats[LONG] = d_long
            
        # Check Short Side (PSQ) vs Index (QQQ)
        if short_df is not None and not short_df.empty and sig_df is not None and not sig_df.empty:
            d_short = log_volatility_decay(
                SHORT, short_df, sig_sym, sig_df,
                leverage=3.0,
                save_daily=True,
                lookback=20
            )
            decay_stats[SHORT] = d_short
    except Exception as e:
        RF.print_log(f"Decay calculation failed (non-blocking): {e}", "RISK")
    
    # Apply decay adjustment to allocation weights
    if decay_stats:
        for sym in [LONG, SHORT]:
            decay_data = decay_stats.get(sym)
            if decay_data and not decay_data.get("note"):
                period_decay = decay_data.get("period_decay_pct", 0.0)
                if period_decay > 1.0:  # 1% decay threshold
                    decay_adjust = max(0.7, 1.0 - (period_decay / 10.0))
                    original_alloc = alloc[sym]
                    alloc[sym] = alloc[sym] * decay_adjust
                    RF.print_log(
                        f"🛡️ Decay adjustment for {sym}: {original_alloc:.4f} → {alloc[sym]:.4f} "
                        f"(decay={period_decay:.2f}%, adjust={decay_adjust:.2f})",
                        "RISK"
                    )

    # Calculate target dollar exposures based on allocator (after decay adjustment)
    tqqq_target_dollars = equity * alloc[LONG]
    sqqq_target_dollars = equity * alloc[SHORT]
    
    # Determine primary target (largest allocation)
    if tqqq_target_dollars > sqqq_target_dollars:
        target_symbol = LONG  # Use dynamic long symbol
        target_dollars = tqqq_target_dollars
        target_direction = "LONG"
    elif sqqq_target_dollars > tqqq_target_dollars:
        target_symbol = SHORT  # Use dynamic short symbol
        target_dollars = sqqq_target_dollars
        target_direction = "LONG"
    else:
        target_symbol = LONG
        target_dollars = 0.0
        target_direction = "FLAT"

    # Create target exposure
    target_price = float((long_df if target_symbol == LONG else short_df)["close"].iloc[-1])
    target_shares = target_dollars / target_price if target_price > 0 else 0.0
    
    target = TargetExposure(
        symbol=target_symbol,
        direction=target_direction,
        dollars=target_dollars,
        shares=target_shares,
        notes=f"Exposure allocator: {LONG}={alloc[LONG]:.2f} {SHORT}={alloc[SHORT]:.2f}"
    )
    RF.print_log(f"Target → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")

    # Breadcrumbs for telemetry (merge with early crumbs from session guard)
    crumbs.update({
        "target_notes": target.notes,
        "signal_underlier": sig_sym,   # NEW
        "phase": phase,   # NEW
        "config_echo": echo,   # NEW: config echo for report/telemetry
    })

    # Compute plan reason (why exposure changed)
    diag = compute_exposure_diagnostics(sig_df)
    plan_reason = format_plan_reason(diag, phase=phase, guard_note=guard_note)
    
    # Log it
    RF.print_log(f"Plan reason → {plan_reason}", "INFO")
    
    # Add to breadcrumbs so telemetry/report can show it
    crumbs.update({"plan_reason": plan_reason})

    # Positions (before)
    positions_before_raw = load_positions()
    RF.print_log(f"Positions BEFORE (raw): {positions_before_raw}", "INFO")
    
    # Reconcile effective positions from fills
    positions_before, pos_note = effective_positions_before(
        raw_positions_before=positions_before_raw,
        broker_positions_snapshot=None  # hook for future: pass real broker positions here if available
    )
    # Normalize symbol casing
    positions_before = map_keys_upper(positions_before)
    RF.print_log(f"Positions effective source: {pos_note}", "INFO")
    RF.print_log(f"Positions BEFORE (effective): {positions_before}", "INFO")
    
    # Store positions source for reporting
    positions_source = pos_note  # 'broker_snapshot' | 'local_fills_applied' | 'raw'

    # Calculate exposure deltas (prev vs desired)
    
    # Build a price map using common date to avoid NaNs
    common_d, px_long, px_short = _last_common_close(long_df, short_df)
    last_prices_map = {
        LONG:  px_long,
        SHORT: px_short,
    }
    # Normalize symbol casing
    last_prices_map = map_keys_upper(last_prices_map)
    
    # Store common date for reporting/telemetry
    common_date_str = common_d.strftime("%Y-%m-%d")
    RF.print_log(f"Price common date → {common_date_str}", "INFO")
    
    # --- Position drift detector (broker vs local) ---
    risk_cfg = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    drc = (risk_cfg.get("drift") or {})
    drift_enabled = bool(drc.get("enabled", True))
    check_syms = [s.upper() for s in (drc.get("symbols") or [LONG, SHORT])]
    shares_eps = float(drc.get("shares_eps", 1.0))
    notional_eps = float(drc.get("notional_eps", 200.0))
    
    # If you have a broker snapshot, set it here; otherwise keep None.
    broker_snapshot = None  # hook: replace with real positions when available
    
    if drift_enabled:
        drift_warn, drift_map, drift_note = compute_position_drift(
            local_pos=positions_before, broker_pos=broker_snapshot, prices=last_prices_map,
            symbols=check_syms, shares_eps=shares_eps, notional_eps=notional_eps
        )
        crumbs.update({
            "drift_note": drift_note,
            "drift_warn": bool(drift_warn),
            "drift_detail": drift_map if drift_map else {},
        })
        if drift_note == "no_broker_snapshot":
            RF.print_log("Drift check: no broker snapshot; skipping.", "INFO")
        elif drift_warn:
            RF.print_log(f"Drift WARN: {drift_map}", "RISK")
        else:
            RF.print_log("Drift OK", "INFO")
    
    # Check data staleness
    from datetime import datetime, timezone
    
    data_cfg = Config(".")._load_yaml("config/data.yaml")
    max_days_ok = int(((data_cfg.get("staleness") or {}).get("max_days_ok", 3)))
    
    today = datetime.now(timezone.utc).date()
    lag_days = (today - common_d.date()).days
    is_stale = lag_days > max_days_ok
    
    if is_stale:
        RF.print_log(f"Price data stale: {lag_days}d old (>{max_days_ok}d)", "RISK")
    
    # Calculate live equity from reconciled positions
    import math
    def _safe(f): 
        try:
            f = float(f); 
            return f if (f == f and math.isfinite(f)) else 0.0
        except Exception: 
            return 0.0

    # live equity (gross) from reconciled positions
    equity_now = 0.0
    for sym, sh in positions_before.items():
        px = _safe(last_prices_map.get(sym))
        equity_now += abs(_safe(sh) * px)

    RF.print_log(f"Positions source → {positions_source} | equity_now=${equity_now:,.2f}", "INFO")

    prev_w = current_exposure_weights(positions_before, last_prices_map, equity_ref=equity, sides=sides)
    dW = exposure_delta(prev_w, alloc, sides=sides)

    # Log concise delta line
    RF.print_log(
        f"Exposure change → {sides[0]} {prev_w[sides[0]]:.2f}→{alloc[sides[0]]:.2f} (Δ{dW[sides[0]]:+.2f}) | "
        f"{sides[1]} {prev_w[sides[1]]:.2f}→{alloc[sides[1]]:.2f} (Δ{dW[sides[1]]:+.2f})",
        "INFO"
    )

    # Apply turnover cap
    # Build a positions_before subset keyed the same way as alloc
    pos_before = {
        LONG:  float(positions_before.get(LONG, 0.0)),
        SHORT: float(positions_before.get(SHORT, 0.0)),
    }

    # Load turnover config
    risk_cfg = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    tov = (risk_cfg.get("turnover") or {})
    max_frac = float(tov.get("max_pct_of_equity", 0.15))
    mode = str(tov.get("mode", "clamp"))

    # Apply turnover cap
    alloc_after_tov, desired_mv_after_tov, turnover_frac, tov_note = enforce_turnover_cap(
        alloc_weights=alloc,
        positions_before=pos_before,
        last_prices=last_prices_map,
        equity=equity,
        max_turnover_frac=max_frac,
        mode=mode,
    )
    
    # Replace alloc with capped version
    alloc = alloc_after_tov
    
    RF.print_log(f"Turnover check → {turnover_frac:.2%} of equity | {tov_note}", "INFO")

    # --- Sanity: mutual exclusivity of sides ---
    san = (risk_cfg.get("sanity") or {}).get("mutual_exclusive_sides", {})
    if bool(san.get("enabled", True)):
        thr = float(san.get("threshold", 0.05))
        ok, note = check_mutual_exclusive(alloc, LONG, SHORT, threshold=thr)
        if not ok:
            action = str(san.get("action", "error")).lower()
            crumbs.update({"sanity_violation": True, "sanity_note": note, "sanity_action": action})
            if action == "clamp":
                alloc = clamp_smaller_side(alloc, LONG, SHORT)
                RF.print_log(f"Sanity clamp → {note}", "RISK")
                # Recompute target after clamping
                tqqq_target_dollars = equity * alloc[LONG]
                sqqq_target_dollars = equity * alloc[SHORT]
                if tqqq_target_dollars > sqqq_target_dollars:
                    target_symbol = LONG
                    target_dollars = tqqq_target_dollars
                    target_direction = "LONG"
                elif sqqq_target_dollars > tqqq_target_dollars:
                    target_symbol = SHORT
                    target_dollars = sqqq_target_dollars
                    target_direction = "LONG"
                else:
                    target_symbol = LONG
                    target_dollars = 0.0
                    target_direction = "FLAT"
                target_price = float((long_df if target_symbol == LONG else short_df)["close"].iloc[-1])
                target_shares = target_dollars / target_price if target_price > 0 else 0.0
                target = TargetExposure(
                    symbol=target_symbol,
                    direction=target_direction,
                    dollars=target_dollars,
                    shares=target_shares,
                    notes=f"Exposure allocator (clamped): {LONG}={alloc[LONG]:.2f} {SHORT}={alloc[SHORT]:.2f}"
                )
                RF.print_log(f"Target updated after clamp → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")
            else:
                RF.print_log(f"Sanity error → {note}", "ERROR")
                # Make the reason explicit in outputs
                crumbs.update({"no_op": True, "no_op_reason": "SANITY_BOTH_SIDES"})
                raise RuntimeError(f"Sanity violation: {note}")
        else:
            crumbs.update({"sanity_violation": False})

    # --- Exposure rounding harmonizer ---
    rnd = (risk_cfg.get("rounding") or {})
    if bool(rnd.get("enabled", True)):
        step = float(rnd.get("share_step", 0.001))
        eps  = float(rnd.get("exposure_epsilon", 0.00005))
        alloc_h, shares_h = harmonize_exposure(prev_w, alloc, last_prices_map, equity_now, step, eps)
        RF.print_log(f"Rounding: step={step} sh; ε={eps:.5f} → weights snapped", "INFO")

        # Replace alloc with harmonized weights for downstream deltas/turnover/planning
        alloc = alloc_h
        
        # Recompute target after harmonization
        tqqq_target_dollars = equity * alloc[LONG]
        sqqq_target_dollars = equity * alloc[SHORT]
        if tqqq_target_dollars > sqqq_target_dollars:
            target_symbol = LONG
            target_dollars = tqqq_target_dollars
            target_direction = "LONG"
        elif sqqq_target_dollars > tqqq_target_dollars:
            target_symbol = SHORT
            target_dollars = sqqq_target_dollars
            target_direction = "LONG"
        else:
            target_symbol = LONG
            target_dollars = 0.0
            target_direction = "FLAT"
        target_price = float((long_df if target_symbol == LONG else short_df)["close"].iloc[-1])
        target_shares = target_dollars / target_price if target_price > 0 else 0.0
        target = TargetExposure(
            symbol=target_symbol,
            direction=target_direction,
            dollars=target_dollars,
            shares=target_shares,
            notes=f"Exposure allocator (harmonized): {LONG}={alloc[LONG]:.2f} {SHORT}={alloc[SHORT]:.2f}"
        )
        RF.print_log(f"Target updated after harmonization → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")
        
        # Stash rounded shares in breadcrumbs for planner/reporting
        crumbs.update({"rounded_shares": {k: round(v, 6) for k,v in shares_h.items()}})
        
        # Recompute delta exposure after harmonization
        dW = exposure_delta(prev_w, alloc, sides=sides)
        RF.print_log(
            f"Exposure change (harmonized) → {sides[0]} {prev_w[sides[0]]:.2f}→{alloc[sides[0]]:.2f} (Δ{dW[sides[0]]:+.2f}) | "
            f"{sides[1]} {prev_w[sides[1]]:.2f}→{alloc[sides[1]]:.2f} (Δ{dW[sides[1]]:+.2f})",
            "INFO"
        )
    else:
        crumbs.update({"rounded_shares": {}})

    # Exposure concentration meter
    mcfg = Config(".")._load_yaml("config/metrics.yaml")
    xcfg = (mcfg.get("exposure_concentration") or {})
    xc_enabled = bool(xcfg.get("enabled", True))
    
    if xc_enabled:
        # Use final desired allocations (post-guards / rounding harmonizer)
        # Create signed map: LONG is positive, SHORT is negative
        signed = {LONG: float(alloc.get(LONG, 0.0)), SHORT: -float(alloc.get(SHORT, 0.0))}
        
        # Net side concentration
        net = side_concentration(signed)
        
        # Single-name concentration (use absolute values for peak)
        abs_weights = {k: abs(v) for k, v in signed.items()}
        sym, peak = symbol_peak(abs_weights)
        
        # Thresholds
        sc = (xcfg.get("side_caps") or {})
        ss = (xcfg.get("symbol_caps") or {})
        side_badge  = badge(net, float(sc.get("warn", 0.80)), float(sc.get("crit", 0.95)))
        sym_badge   = badge(peak, float(ss.get("warn", 0.80)), float(ss.get("crit", 0.95)))
        
        crumbs.update({
            "exposure_concentration": {
                "net_abs": round(net, 4),
                "net_badge": side_badge,
                "peak_symbol": sym,
                "peak_abs": round(peak, 4),
                "peak_badge": sym_badge,
            }
        })

    # Add to breadcrumbs for report/telemetry
    crumbs.update({
        "exec_long": LONG,
        "exec_short": SHORT,
        "prev_exposure": { s: round(prev_w[s], 4) for s in sides },
        "desired_exposure": { s: round(alloc[s], 4) for s in sides },
        "delta_exposure": { s: round(dW[s], 4) for s in sides },
        "turnover_frac": round(turnover_frac, 4),
        "turnover_note": tov_note,
        "positions_source": positions_source,
        "equity_now": round(equity_now, 2),
        "price_common_date": common_date_str,
        "price_staleness_days": lag_days,
        "price_stale": bool(is_stale),
        "price_stale_note": f"{lag_days}d old (> {max_days_ok}d)" if is_stale else "fresh",
        "run_duration_sec": round(time.perf_counter() - t0, 3),
        "versions": runtime_versions(),
    })

    # Plan intents
    price = float((long_df if target.symbol == LONG else short_df)["close"].iloc[-1])
    intents: List[OrderIntent] = plan_orders(
        current_positions=positions_before,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=min_trade_value,
        emergency_override=False,
    )
    
    # Normalize symbol casing in intents
    intents = [
        OrderIntent(
            symbol=sym_upper(intent.symbol),
            side=intent.side,
            qty=intent.qty,
            order_type=intent.order_type,
            time_in_force=intent.time_in_force,
            limit_price=intent.limit_price,
            reason=intent.reason
        ) for intent in intents
    ]

    # Order preview CSV (when dry_run=true)
    broker_cfg = Config(".")._load_yaml("config/broker.yaml")
    dry_run_flag = bool((broker_cfg.get("alpaca") or {}).get("dry_run", True))
    
    if dry_run_flag and intents:
        preview_meta = {
            "exec_long": crumbs.get("exec_long", ""),
            "exec_short": crumbs.get("exec_short", ""),
            "price_common_date": crumbs.get("price_common_date", ""),
            "turnover_note": crumbs.get("turnover_note", ""),
            "no_op": crumbs.get("no_op", False),
            "no_op_reason": crumbs.get("no_op_reason", ""),
            "config_hash16": crumbs.get("config_hash16", ""),
        }
        try:
            p = write_order_preview([_intent_to_dict(it) for it in intents], meta=preview_meta)
            RF.print_log(f"Order preview CSV saved → {p}", "INFO")
        except Exception as e:
            RF.print_log(f"Order preview CSV failed: {e}", "ERROR")

    # Cadence guard: filter intents based on recent trades
    risk_cfg = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    cad = (risk_cfg.get("cadence") or {})
    cad_enabled = bool(cad.get("enabled", True))
    cad_min_days = int(cad.get("min_days_between", 1))
    cad_symbols = [s.upper() for s in (cad.get("symbols") or [])]

    def _cadence_block(it) -> bool:
        """Return True if this intent should be blocked by cadence."""
        sym = str(it.symbol).upper()
        if cad_symbols and sym not in cad_symbols:
            return False
        d = days_since_trade(sym)
        if d is None:
            return False  # never traded before
        return d < cad_min_days

    if cad_enabled and intents:
        kept, blocked = [], []
        for it in intents:
            if _cadence_block(it):
                blocked.append(it)
            else:
                kept.append(it)
        if blocked and not kept:
            # Entire day is a no-op due to cadence
            crumbs.update({"no_op": True, "no_op_reason": "CADENCE_GUARD"})
            RF.print_log(f"Cadence guard: blocked {len(blocked)} intent(s) (<{cad_min_days}d since last trade)", "RISK")
        elif blocked:
            RF.print_log(f"Cadence guard: filtered {len(blocked)} of {len(intents)} intent(s)", "RISK")
        intents = kept

    # Add cadence info to breadcrumbs
    crumbs.update({
        "cadence_enabled": cad_enabled,
        "cadence_min_days": cad_min_days,
    })

    # --- Exposure delta filter ---
    ex_cfg = (risk_cfg.get("exposure_threshold") or {})
    ex_enabled = bool(ex_cfg.get("enabled", True))
    ex_min = float(ex_cfg.get("min_delta_abs", 0.01))

    if ex_enabled and intents:
        kept, filtered = [], []
        for it in intents:
            sym = str(it.symbol).upper()
            d_prev = float((crumbs.get("prev_exposure") or {}).get(sym, 0.0))
            d_new  = float((crumbs.get("desired_exposure") or {}).get(sym, 0.0))
            delta  = abs(d_new - d_prev)
            if delta < ex_min:
                filtered.append(it)
            else:
                kept.append(it)
        if filtered and not kept:
            crumbs.update({"no_op": True, "no_op_reason": "DELTA_BELOW_THRESHOLD"})
            RF.print_log(f"Exposure filter: all intents below {ex_min:.2%}, skipped.", "RISK")
        elif filtered:
            RF.print_log(f"Exposure filter: {len(filtered)} of {len(intents)} intents below {ex_min:.2%}, skipped.", "RISK")
        intents = kept

    # Add exposure threshold info to breadcrumbs
    crumbs.update({
        "exposure_min_delta": ex_min,
    })

    # Coalescing (side flip optimization)
    risk_cfg = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    coal = (risk_cfg.get("coalescing") or {})
    if bool(coal.get("enabled", True)):
        c_intents, c_note = coalesce_side_flip(
            positions_before=positions_before,
            target_weights=alloc,
            prices=last_prices_map,
            equity=equity_now,
            long_sym=LONG,
            short_sym=SHORT,
            close_dust_shares=float(coal.get("close_dust_shares", 1.0)),
            min_open_notional=float(coal.get("min_open_notional", 200.0)),
            prefer_single_leg_if_net_small=bool(coal.get("prefer_single_leg_if_net_small", True)),
        )
        if c_intents:
            RF.print_log(f"Coalesced flip → {c_note}; intents={len(c_intents)}", "INFO")
            # Convert coalesced dict intents to OrderIntent objects
            intents = [
                OrderIntent(
                    symbol=sym_upper(intent["symbol"]),
                    side=intent["side"].upper(),
                    qty=float(intent["qty"]),
                    order_type="market",  # default for coalesced intents
                    time_in_force="day",  # default for coalesced intents
                    limit_price=None,
                    reason=intent["reason"]
                ) for intent in c_intents
            ]
            crumbs.update({"coalesced_flip": True, "coalesce_note": c_note})
        else:
            crumbs.update({"coalesced_flip": False, "coalesce_note": c_note})

    # Cash detection: both sides zero after all adjustments
    is_cash = abs(float(alloc.get(LONG, 0.0))) <= 1e-9 and abs(float(alloc.get(SHORT, 0.0))) <= 1e-9

    if is_cash:
        # explicit breadcrumbs & target
        crumbs.update({
            "cash_mode": True,
            "no_op": True,
            "no_op_reason": crumbs.get("no_op_reason", "") or "CASH_TARGET",
        })

        target = TargetExposure(
            symbol="CASH",
            direction="FLAT",
            dollars=0.0,
            shares=0.0,
            notes="All exposures clamped/filtered to 0",
        )

        # ensure we emit no orders
        intents = []
        RF.print_log("Cash mode: both sides zero → CASH target", "INFO")
    else:
        crumbs.update({"cash_mode": False})

    # If no intents, derive a reason so we can explain the no-op day.
    if not intents:
        # 1) If turnover rule said skip
        tov_note = crumbs.get("turnover_note", "")
        if isinstance(tov_note, str) and "skip" in tov_note.lower():
            noop_reason = "TURNOVER_SKIP"
        else:
            # 2) If desired == current exposure within epsilon → no change
            sides = [exec_map["long"], exec_map["short"]]
            try:
                eps = 1e-4
                desired_w = [float(alloc.get(s, 0.0)) for s in sides]
                # recompute prev_w against equity_now to avoid key/equity drift
                prev_w_map = current_exposure_weights(positions_before, last_prices_map, equity_now, sides)
                prev_w = [float(prev_w_map.get(s, 0.0)) for s in sides]
                if all(abs(d - p) <= eps for d, p in zip(desired_w, prev_w)):
                    noop_reason = "NO_CHANGE"
                else:
                    # 3) Otherwise assume sizing/threshold filtered out tiny trade(s)
                    noop_reason = "SIZING_FILTER"
            except Exception:
                noop_reason = "NO_CHANGE"

        crumbs.update({"no_op": True, "no_op_reason": noop_reason})
    else:
        crumbs.update({"no_op": False})

    audit = ENSStyleAudit()

    if not intents:
        RF.print_log("No trade planned (flat, blocked, or below threshold).", "SUCCESS")
        
        # Update crumbs with config hash before heartbeat
        crumbs.update({"config_hash16": cfg_short})
        attach_model_manifest(crumbs)
        
        # Store execution mode
        exec_mode = dry_run_details(".")
        crumbs["execution_mode"] = exec_mode
        # Log dry-run if forced by ENV
        if exec_mode.get("dry_run") and exec_mode.get("source") == "env":
            incidents.log(
                "INFO",
                "Run executed in DRY-RUN mode due to environment variable",
                {"env": exec_mode}
            )
        # Log no-op decision
        if crumbs.get("no_op", False):
            incidents.log(
                "INFO",
                "No-op decision executed",
                {
                    "reason": crumbs.get("no_op_reason", ""),
                    "allocation": crumbs.get("allocation", {}),
                }
            )
        
        # --- Daily heartbeat telemetry (early return path) ---
        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
        hb = (tel_cfg.get("heartbeat") or {})
        if bool(hb.get("enabled", True)) and tel_cfg.get("enabled", True):
            try:
                env = load_env()
                notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
                notifier.send_heartbeat(crumbs)
                RF.print_log("Heartbeat sent.", "SUCCESS")
            except Exception as e:
                RF.print_log(f"Heartbeat failed: {e}", "ERROR")
        
        # Optional: stdout heartbeat (always log, even if Telegram disabled)
        RF.print_log(
            f"HB | {crumbs.get('config_hash16','??')} · {crumbs.get('price_common_date','????-??-??')} · "
            f"{crumbs.get('exec_long','')}/{crumbs.get('exec_short','')} · {crumbs.get('run_duration_sec',0):.2f}s · "
            f"{'no-op '+str(crumbs.get('no_op_reason','')) if crumbs.get('no_op') else 'active'}",
            "INFO"
        )
        
        return {
            "target": asdict(target),
            "positions_before": positions_before,
            "intents": [],
            "positions_after": positions_before,
            "breadcrumbs": crumbs,
            "config_fingerprint": fp
        }

    # Log PLAN records
    for it in intents:
        audit.log(kind="PLAN", data=_intent_to_dict(it))

    # --- Optional: place with Alpaca if enabled in config ---
    broker_cfg = Config(".")._load_yaml("config/broker.yaml") if (Config(".").root / "config/broker.yaml").exists() else {}
    alp = (broker_cfg.get("alpaca") or {})
    do_broker = bool(alp.get("enabled", True))  # default on, controlled by dry_run anyway
    
    # Use is_dry_run() to check ENV var and config (respects REGIMEFLEX_DRY_RUN=1)
    from .exec_alpaca import is_dry_run
    dry_run_broker = is_dry_run(".")
    
    mode = str(alp.get("mode", "paper")).lower()
    base_url = ALPACA_PAPER_URL if (mode == "paper") else ALPACA_LIVE_URL

    # Check envs only if we intend to place real orders
    env_issues = env_guard(broker_cfg)
    
    forced_dry = False
    missing_flat = {k: v for k, v in env_issues.items()}  # copy for breadcrumbs
    
    if mode in ("paper", "live") and not dry_run_broker:
        # we are about to trade — verify creds
        if "alpaca" in env_issues:
            # Flip to dry_run for safety
            dry_run_broker = True
            forced_dry = True
            RF.print_log(f"ENV GUARD: Missing broker env → forcing dry_run. Missing: {env_issues['alpaca']}", "RISK")
    
    # Persist in breadcrumbs
    if missing_flat:
        crumbs.update({"env_missing": missing_flat})
    crumbs.update({
        "dry_run": dry_run_broker,
        "env_forced_dry_run": forced_dry,
    })

    env = load_env()
    exe = AlpacaExecutor(AlpacaCreds(key=env.alpaca_key, secret=env.alpaca_secret, base_url=base_url),
                         dry_run=dry_run_broker)

    # Liquidity depth probe
    liq_cfg = Config(".")._load_yaml("config/metrics.yaml").get("liquidity_depth", {}) or {}
    adv_map = {}
    intents_dict = []
    
    if bool(liq_cfg.get("enabled", True)) and intents:
        win = int(liq_cfg.get("adv_window", 20))
        warn = float(liq_cfg.get("warn_frac", 0.05))
        crit = float(liq_cfg.get("crit_frac", 0.10))
        
        # Build ADV map for any symbols that appear in intents (usually QQQ/PSQ)
        for sym in { (i.symbol if hasattr(i, 'symbol') else str(i.get("symbol",""))).upper() for i in intents }:
            if sym == LONG:
                adv_map[sym] = rolling_adv(long_df, win)
            elif sym == SHORT:
                adv_map[sym] = rolling_adv(short_df, win)
            else:
                adv_map[sym] = 0.0  # unknown symbol → 0 (will render as GREEN unless qty>0 and adv=0)
        
        # Convert intents to dict format with price field
        for it in intents:
            it_dict = _intent_to_dict(it)
            # Use limit_price if available, otherwise fall back to last_prices_map
            if it_dict.get("limit_price") is not None:
                it_dict["price"] = it_dict["limit_price"]
            else:
                it_dict["price"] = float(last_prices_map.get(it_dict["symbol"], 0.0))
            intents_dict.append(it_dict)
        
        liq = assess_depth(intents_dict, adv_map, warn_frac=warn, crit_frac=crit)
        crumbs.update({"liquidity_depth": liq})

        # --- Liquidity Z-Score Check (Blocking) ---
        # Ref: Institutional-Grade Entry (delay if volume is 2 SD below mean)
        # We check the primary intent symbol's volume.
        blocked_by_liq = False
        liq_block_reason = ""
        for it in intents:
            sym = str(it.symbol).upper()
            if sym == LONG:
                df_hist = long_df
            elif sym == SHORT:
                df_hist = short_df
            else:
                 continue # skip unknown symbols
            
            # Current volume: assume last row of df is "current" (or yesterday if running at open)
            # If running intraday, df should be up to date. 
            # If running at open (Morning Rush), we might be looking at yesterday's volume?
            # The prompt implies checking "current volume", so likely intraday current.
            # We'll use the last available bar's volume.
            curr_vol = float(df_hist["volume"].iloc[-1]) if not df_hist.empty else 0.0
            
            # Institutional-Grade Entry: Liquidity Check
            # Delay entry by 30 minutes if volume is 2 SD below mean
            z_check = check_zscore_liquidity(
                sym, curr_vol, df_hist, 
                window=20, 
                z_thresh=-2.0,
                delay_minutes=30
            )
            
            if z_check.get("blocked"):
                blocked_by_liq = True
                liq_block_reason = z_check["reason"]
                retry_after = z_check.get("retry_after", "")
                crumbs.update({
                    "liquidity_z_score": z_check,
                    "no_op": True,
                    "no_op_reason": "LIQUIDITY_DELAY",
                    "liquidity_retry_after": retry_after,
                    "liquidity_delay_minutes": z_check.get("delay_minutes", 30)
                })
                RF.print_log(
                    f"Liquidity Guard: {liq_block_reason} → Delaying entry by {z_check.get('delay_minutes', 30)} minutes. Retry after: {retry_after}",
                    "RISK"
                )
                break
        
        if blocked_by_liq:
             # Clear intents to delay execution
             intents = []
             result_intents = [] # Update result wrapper too if needed, but intents var is what matters for downstream execution
             
    # --- Volatility Decay Logger ---
    # Institutional-Grade Entry: Leverage Decay Logger
    # Calculate and log 'Volatility Decay' on TQQQ/SQQQ holdings daily, comparing
    # our performance against the raw QQQ index to ensure the 'Swing' strategy
    # is actually outperforming.
    decay_stats = {}
    try:
        # Check Long Side (TQQQ) vs Index (QQQ)
        if long_df is not None and not long_df.empty and sig_df is not None and not sig_df.empty:
            d_long = log_volatility_decay(
                LONG, long_df, sig_sym, sig_df,
                leverage=3.0,
                save_daily=True,
                lookback=20
            )
            decay_stats[LONG] = d_long
            
        # Check Short Side (PSQ) vs Index (QQQ)
        if short_df is not None and not short_df.empty and sig_df is not None and not sig_df.empty:
            d_short = log_volatility_decay(
                SHORT, short_df, sig_sym, sig_df,
                leverage=3.0,  # PSQ is inverse, but we track vs QQQ
                save_daily=True,
                lookback=20
            )
            decay_stats[SHORT] = d_short
            
        crumbs.update({"volatility_decay": decay_stats})
        
        # Log summary with performance comparison
        for sym, d in decay_stats.items():
            if d.get("note"):
                continue  # Skip if missing data
                
            daily_error = d.get('daily_tracking_error_bps', 0)
            period_decay = d.get('period_decay_pct', 0)
            outperforming = d.get('outperforming', False)
            edge_status = "✅ OUTPERFORMING" if outperforming else "⚠️ UNDERPERFORMING"
            
            RF.print_log(
                f"Decay {sym}: {daily_error}bps daily error | {period_decay}% period drift ({d.get('lookback_days')}d) | {edge_status}",
                "SUCCESS" if outperforming else "RISK"
            )
            
            # Alert if strategy is underperforming significantly
            if not outperforming and abs(period_decay) > 2.0:
                RF.print_log(
                    f"⚠️ Strategy Edge Warning: {sym} decay {period_decay}% suggests strategy may not be outperforming",
                    "RISK"
                )
             
    except Exception as e:
        RF.print_log(f"Decay logger failed: {e}", "ERROR")
    
    # ADV guardrail (reuse adv_map and intents_dict from liquidity depth probe, or build if needed)
    risk_cfg_ag = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    ag = (risk_cfg_ag.get("adv_guardrail") or {})
    ag_enabled = bool(ag.get("enabled", True))
    
    if ag_enabled and intents:
        # Build adv_map and intents_dict if not already built by liquidity depth probe
        if len(adv_map) == 0 or len(intents_dict) == 0:
            liq_cfg_fallback = Config(".")._load_yaml("config/metrics.yaml").get("liquidity_depth", {}) or {}
            win = int(liq_cfg_fallback.get("adv_window", 20))
            for sym in { (i.symbol if hasattr(i, 'symbol') else str(i.get("symbol",""))).upper() for i in intents }:
                if sym == LONG:
                    adv_map[sym] = rolling_adv(long_df, win)
                elif sym == SHORT:
                    adv_map[sym] = rolling_adv(short_df, win)
                else:
                    adv_map[sym] = 0.0
            
            for it in intents:
                it_dict = _intent_to_dict(it)
                if it_dict.get("limit_price") is not None:
                    it_dict["price"] = it_dict["limit_price"]
                else:
                    it_dict["price"] = float(last_prices_map.get(it_dict["symbol"], 0.0))
                intents_dict.append(it_dict)
        
        res = enforce_adv_cap(
            intents=intents_dict,
            adv_map=adv_map,
            crit_frac=float(ag.get("crit_frac", 0.10)),
            action=str(ag.get("action", "block")),
        )
        
        if res.get("violations"):
            crumbs.update({"adv_guardrail": {
                "action": str(ag.get("action", "block")).lower(),
                "crit_frac": float(ag.get("crit_frac", 0.10)),
                "violations": res["violations"]
            }})
            
            if res.get("blocked", False):
                RF.print_log("ADV guardrail: violation → run blocked (no orders).", "RISK")
                crumbs.update({"no_op": True, "no_op_reason": "ADV_GUARD"})
                target = TargetExposure(
                    symbol="CASH",
                    direction="FLAT",
                    dollars=0.0,
                    shares=0.0,
                    notes="adv_guard_block"
                )
                result = {
                    "target": target,
                    "positions_before": positions_before,
                    "intents": [],
                    "positions_after": positions_before,
                    "breadcrumbs": crumbs,
                }
                return result
            else:
                # Scale mode: update intents_dict and convert back to OrderIntent objects
                RF.print_log("ADV guardrail: scaling violating intents to cap.", "RISK")
                scaled_dicts = res.get("scaled_intents", intents_dict)
                # Convert scaled dicts back to OrderIntent objects
                intents = []
                for it_dict in scaled_dicts:
                    intents.append(OrderIntent(
                        symbol=sym_upper(it_dict["symbol"]),
                        side=it_dict["side"].upper(),
                        qty=float(it_dict["qty"]),
                        order_type=it_dict.get("order_type", "market"),
                        time_in_force=it_dict.get("time_in_force", "day"),
                        limit_price=it_dict.get("limit_price"),
                        reason=it_dict.get("reason", "adv_guard_scaled")
                    ))

    # Kill-switch guard: hard block if conditions are met
    risk_cfg_ks = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    kill_result = evaluate_kill_switch(crumbs, risk_cfg_ks)
    crumbs["kill_switch"] = kill_result  # store in breadcrumbs for replay/HTML
    
    if kill_result["triggered"]:
        # Hard block for this run
        reason_text = "; ".join(kill_result["reasons"])
        existing_no_op = crumbs.get("no_op", False)
        existing_reason = crumbs.get("no_op_reason", "")
        
        crumbs.update({
            "no_op": True,
        })
        
        # Append kill-switch reason
        if existing_reason:
            crumbs["no_op_reason"] = existing_reason + " | kill_switch: " + reason_text
        else:
            crumbs["no_op_reason"] = "kill_switch: " + reason_text
        
        RF.print_log(f"Kill-switch TRIGGERED: {reason_text}", "RISK")
        
        # Ensure no intents / no orders
        intents = []
        target = TargetExposure(
            symbol="CASH",
            direction="FLAT",
            dollars=0.0,
            shares=0.0,
            notes="kill_switch_block"
        )
        
        # Early return with no-op result
        return {
            "target": asdict(target),
            "positions_before": positions_before,
            "intents": [],
            "positions_after": positions_before,
            "breadcrumbs": crumbs,
            "config_fingerprint": fp
        }

    # Anomaly detection: soft thresholds (log warnings, don't block)
    # This runs after kill-switch but before panic guard
    # We use the same risk_cfg_ks that was loaded for kill-switch
    anomalies = detect_anomalies(crumbs, risk_cfg_ks)
    crumbs["anomalies"] = anomalies  # store for replay/report/status
    
    if anomalies.get("any"):
        # Slippage anomaly
        sl = anomalies.get("slippage", {}) or {}
        if sl.get("flagged") and sl.get("reason"):
            incidents.log(
                "WARNING",
                "Slippage anomaly detected",
                {"reason": sl["reason"], "metrics": crumbs.get("metrics", {})},
            )
        
        # Liquidity anomaly
        lq = anomalies.get("liquidity", {}) or {}
        if lq.get("flagged") and lq.get("reason"):
            incidents.log(
                "WARNING",
                "Liquidity anomaly detected",
                {"reason": lq["reason"], "guards": crumbs.get("guards", {})},
            )

    # Price source sanity check: validate presence and basic structure
    ps_check = check_price_source(crumbs)
    crumbs["price_source_check"] = ps_check
    
    if not ps_check.get("ok", False):
        # Log an incident; this does NOT block trading,
        # it only records that metadata is missing or malformed.
        incidents.log(
            "WARNING",
            "Price source metadata check failed",
            {"reason": ps_check.get("reason", "")}
        )

    # Panic guard: prepare context snapshot
    risk_cfg = Config(".")._load_yaml("config/risk.yaml") if (Config(".").root / "config/risk.yaml").exists() else {}
    pg_cfg = (risk_cfg.get("panic_guard") or {})
    pg_enabled = bool(pg_cfg.get("enabled", True))
    pg_dir = Path(str(pg_cfg.get("out_dir", "logs/audit")))
    pg_file = str(pg_cfg.get("filename", "panic.json"))
    pg_tel = bool(pg_cfg.get("telegram_alert", True))

    # Build a lightweight context snapshot (no assumptions; use what you already have)
    panic_ctx = {
        "equity_now": equity_now,
        "last_prices_map": last_prices_map,
        "positions_before": positions_before,
        "alloc": alloc,
        "prev_exposure": crumbs.get("prev_exposure", {}),
        "desired_exposure": crumbs.get("desired_exposure", {}),
        "delta_exposure": crumbs.get("delta_exposure", {}),
        "turnover_frac": crumbs.get("turnover_frac", None),
        "exec_pair": {"long": LONG, "short": SHORT},
        "dry_run": crumbs.get("dry_run", False),
        "config_hash16": crumbs.get("config_hash16", ""),
        "price_common_date": crumbs.get("price_common_date", ""),
    }

    try:
        # Safety: Stale Data Check
        try:
            from .safety_wrapper import SafetyWrapper, StaleDataError
            safety = SafetyWrapper()
            if long_df is not None and not long_df.empty:
                # Check freshness of the last bar (assume it's the latest available data)
                # Ensure we handle timezone-aware vs naive correctly (data.py handles normalization)
                last_ts = long_df.index[-1]
                if hasattr(last_ts, "to_pydatetime"):
                    last_ts = last_ts.to_pydatetime()
                # Safety wrapper handles timezone conversion
                # This compares Polygon data timestamp with system time
                is_fresh, age_seconds, msg = safety.validate_freshness(last_ts, raise_on_stale=True)
                RF.print_log(f"🛡️ Safety Check: {msg}", "SUCCESS")
        except ImportError:
            pass  # Safety wrapper not available
        except StaleDataError as e:
            RF.print_log(f"⛔ SAFETY SHIELD: {e}", "ERROR")
            # Send alert through Guardian module
            try:
                from .guardian.alerting import get_alert_manager
                alert_mgr = get_alert_manager()
                alert_mgr.send_warning(
                    "Stale Data Detected",
                    f"Trading aborted: {str(e)}"
                )
            except Exception:
                pass  # Best effort alert
            
            # Abort trading for this cycle
            crumbs.update({"no_op": True, "no_op_reason": "STALE_DATA_SHIELD"})
            raise  # Re-raise to skip execution and trigger fail status

        broker_results = []
        if do_broker and intents:
            RF.print_log(f"Broker path: mode={alp.get('mode','paper')} dry_run={dry_run_broker}", "INFO")
            # Prepare mid prices for slippage protection (use last close as mid)
            mid_prices = {sym.upper(): float(last_prices_map.get(sym.upper(), 0.0)) 
                         for sym in set(it.symbol.upper() for it in intents)}
            broker_results = exe.place_orders(intents, mid_prices=mid_prices)
            # Audit ORDER results (payloads if dry-run, API responses if live)
            for res in broker_results:
                audit.log(kind="ORDER", data={k: v for k, v in res.items()})
        else:
            RF.print_log("Broker path skipped (disabled or no intents).", "INFO")

        # Reconciliation (plan vs acknowledged/payload)
        if broker_results:
            rec = compare_intents_vs_orders(intents, broker_results)
            RF.print_log(f"Reconcile: matches={len(rec['matches'])} mismatches={len(rec['mismatches'])} "
                         f"unmatched_intents={len(rec['unmatched_intents'])}", "INFO")

        # Execution quality tracking setup
        eq_cfg = Config(".")._load_yaml("config/metrics.yaml").get("execution_quality", {}) or {}
        eq_enabled = bool(eq_cfg.get("enabled", True))
        eq_ref = str(eq_cfg.get("ref", "close")).lower()
        eq_store = Path(str(eq_cfg.get("store_path", "logs/audit/fills.jsonl")))
        eq_window = int(eq_cfg.get("window", 20))
        
        def get_ref_price(sym: str) -> float | None:
            if eq_ref == "close":
                return float(last_prices_map.get(sym.upper(), 0.0))
            # If you later add mid/last, wire them here using your own sources.
            return float(last_prices_map.get(sym.upper(), 0.0))
        
        # Simulate fills → update positions → FILL records
        fills = simulate_fills(intents, last_price=price)
        positions_after = apply_simulated_fills(positions_before, fills)
        save_positions(positions_after)
        for f in fills:
            audit.log(kind="FILL", data={
                "symbol": f.symbol, "side": f.side,
                "qty": round(float(f.qty), 6), "price": float(f.price), "note": f.note
            })
            
            # Log fill for execution quality
            if eq_enabled:
                ref_px = get_ref_price(f.symbol)
                slip = slippage_bps(f.side, float(f.price), float(ref_px) if ref_px else 0.0)
                append_fill(eq_store, {
                    "symbol": f.symbol.upper(),
                    "side": f.side.upper(),
                    "qty": float(f.qty),
                    "fill_price": float(f.price),
                    "ref_kind": eq_ref,
                    "ref_price": float(ref_px) if ref_px else None,
                    "slip_bps": slip,
                    "exec_pair": {"long": LONG, "short": SHORT},
                    "config_hash16": crumbs.get("config_hash16", ""),
                    "as_of": crumbs.get("price_common_date", "")
                })
        
        # Summarize execution quality after all fills
        eq_summary = {}
        if eq_enabled:
            last_fills = load_fills(eq_store, limit=eq_window)
            stats = rolling_stats(last_fills, window=eq_window)
            eq_summary = {
                "window": eq_window,
                "count": int(stats["count"]),
                "avg_bps": None if stats["avg_bps"] is None else round(stats["avg_bps"], 2),
                "p95_bps": None if stats["p95_bps"] is None else round(stats["p95_bps"], 2),
                "ref": eq_ref
            }
            crumbs.update({"exec_quality": eq_summary})
            
            # Fill-quality drift alarm
            fq_cfg = Config(".")._load_yaml("config/metrics.yaml").get("fill_quality_drift", {}) or {}
            if bool(fq_cfg.get("enabled", True)):
                store = Path(str(fq_cfg.get("store_path", "logs/audit/fills.jsonl")))
                rows = load_jsonl(store)
                summary, alert = assess_drift(
                    rows=rows,
                    baseline_days=int(fq_cfg.get("baseline_days", 30)),
                    compare_window=int(fq_cfg.get("compare_window", 20)),
                    worsen_bps=float(fq_cfg.get("worsen_bps", 3.0)),
                )
                crumbs.update({"fill_quality_drift": {**summary, "threshold_bps": float(fq_cfg.get("worsen_bps", 3.0)), "alert": bool(alert), "baseline_days": int(fq_cfg.get("baseline_days", 30))}})
                if alert:
                    RF.print_log(f"Fill-quality drift ALERT: current {summary['current_avg']}bps vs baseline {summary['baseline_avg']}bps (Δ {summary['delta_bps']}bps)", "RISK")
                    # Optional Telegram ping (short)
                    try:
                        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
                        if tel_cfg.get("enabled", True):
                            env_tele = load_env()
                            notifier = Notifier(TGCreds(token=env_tele.telegram_bot_token, chat_id=env_tele.telegram_chat_id))
                            notifier.send(f"⚠️ *Fill-quality drift*: {summary['current_avg']}bps vs {summary['baseline_avg']}bps (Δ {summary['delta_bps']}bps > {fq_cfg.get('worsen_bps',3.0)}bps)")
                    except Exception:
                        RF.print_log("Fill-quality drift Telegram alert failed.", "ERROR")
    except Exception as e:
        RF.print_log(f"PANIC GUARD: exception during execution: {e}", "ERROR")
        if pg_enabled and intents:
            try:
                intents_dict = [_intent_to_dict(it) for it in intents]
                p = write_panic_bundle(pg_dir, pg_file, intents=intents_dict, crumbs=crumbs, context=panic_ctx)
                RF.print_log(f"Panic bundle written → {p}", "RISK")
                if pg_tel:
                    try:
                        tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
                        if tel_cfg.get("enabled", True):
                            env_tele = load_env()
                            notifier = Notifier(TGCreds(token=env_tele.telegram_bot_token, chat_id=env_tele.telegram_chat_id))
                            notifier.send(f"⚠️ *Panic guard*: execution error. Bundle: `{p.as_posix()}`")
                    except Exception:
                        RF.print_log("Panic Telegram alert failed.", "ERROR")
            except Exception as werr:
                RF.print_log(f"Panic bundle failed: {werr}", "ERROR")
        # Update breadcrumbs to indicate panic was triggered
        crumbs.update({"panic_guard_triggered": True})
        # re-raise so health shows FAIL and CI catches it
        raise

    RF.print_log(f"Positions AFTER: {positions_after}", "INFO")
    RF.print_log("Offline daily cycle complete", "SUCCESS")
    
    # Log run duration
    duration_sec = round(time.perf_counter() - t0, 3)
    RF.print_log(f"Run duration → {duration_sec:.3f}s", "INFO")

    # Daily PnL/Exposure snapshot
    try:
        equity_ref = float(Config(".").run.get("equity", 25000.0))
    except Exception:
        equity_ref = 25000.0

    # Last prices for valuation
    last_prices = {
        LONG: float(long_df["close"].iloc[-1]),
        SHORT: float(short_df["close"].iloc[-1]),
    }

    snap = snapshot_from_positions(positions_after, last_prices, equity_ref)
    append_snapshot_csv(snap)

    # Log rotation at end of daily run (config-gated)
    logs_cfg = Config(".")._load_yaml("config/logs.yaml") if (Config(".").root / "config/logs.yaml").exists() else {}
    if logs_cfg.get("rotate_on_run", True):
        rotate_all()

    # Build final result for return
    result = {
        "target": asdict(target),
        "positions_before": positions_before,
        "intents": [_intent_to_dict(it) for it in intents],
        "positions_after": positions_after,
        "breadcrumbs": {**crumbs, "config_hash16": fp["sha256_16"]},
        "snapshot": snap,
        "config_fingerprint": fp
    }

    # Export CSV change report
    try:
        csv_path = write_change_report(result)
        RF.print_log(f"CSV change report saved → {csv_path}", "INFO")
    except Exception as e:
        RF.print_log(f"CSV export failed: {e}", "ERROR")

    # Append run summary JSONL
    try:
        path = append_run_summary(result)
        RF.print_log(f"Run summary appended → {path}", "INFO")
    except Exception as e:
        RF.print_log(f"Run summary append failed: {e}", "ERROR")

    # Compressed logs rotation (gzip old logs)
    rep_cfg = Config(".")._load_yaml("config/reports.yaml") if (Config(".").root / "config/reports.yaml").exists() else {}
    lr = (rep_cfg.get("logs_rotation") or {})
    if bool(lr.get("enabled", True)):
        patterns = [str(x) for x in (lr.get("include") or [])]
        days_old = int(lr.get("days_old", 7))
        exclude_gz = bool(lr.get("exclude_gz", True))
        rotated = rotate_logs(patterns, days_old=days_old, exclude_gz=exclude_gz)
        if rotated:
            RF.print_log(f"Log rotation: compressed {len(rotated)} file(s).", "INFO")
        else:
            RF.print_log("Log rotation: nothing to compress.", "INFO")

    # Metrics: Turnover Stability Index (TSI)
    met_cfg = Config(".")._load_yaml("config/metrics.yaml") if (Config(".").root / "config/metrics.yaml").exists() else {}
    tsi_cfg = (met_cfg.get("turnover_stability") or {})
    tsi_win = int(tsi_cfg.get("window_days", 7))
    tsi_warn = float(tsi_cfg.get("warn_threshold", 0.25))

    tsi = compute_tsi(tsi_win)
    tsi_warn_flag = bool(tsi["avg_turnover"] > tsi_warn)

    crumbs.update({
        "tsi_window_days": tsi_win,
        "tsi_avg_turnover": round(tsi["avg_turnover"], 4),
        "tsi_days_count": tsi["count_days"],
        "tsi_warn": tsi_warn_flag,
        "tsi_warn_threshold": tsi_warn,
    })

    if tsi_warn_flag:
        RF.print_log(f"TSI warn: avg turnover {tsi['avg_turnover']:.2%} over {tsi_win}d exceeds {tsi_warn:.2%}", "RISK")

    # Update crumbs with config hash before heartbeat
    crumbs.update({"config_hash16": fp["sha256_16"]})
    attach_model_manifest(crumbs)
    
    # Store execution mode (live vs dry-run and source)
    exec_mode = dry_run_details(".")
    crumbs["execution_mode"] = exec_mode
    # Log dry-run if forced by ENV
    if exec_mode.get("dry_run") and exec_mode.get("source") == "env":
        incidents.log(
            "INFO",
            "Run executed in DRY-RUN mode due to environment variable",
            {"env": exec_mode}
        )
    # Log no-op decision
    if crumbs.get("no_op", False):
        incidents.log(
            "INFO",
            "No-op decision executed",
            {
                "reason": crumbs.get("no_op_reason", ""),
                "allocation": crumbs.get("allocation", {}),
            }
        )

    # --- Daily heartbeat telemetry ---
    tel_cfg = Config(".")._load_yaml("config/telemetry.yaml") if (Config(".").root / "config/telemetry.yaml").exists() else {}
    hb = (tel_cfg.get("heartbeat") or {})
    if bool(hb.get("enabled", True)) and tel_cfg.get("enabled", True):
        try:
            env = load_env()
            notifier = Notifier(TGCreds(token=env.telegram_bot_token, chat_id=env.telegram_chat_id))
            notifier.send_heartbeat(crumbs)
            RF.print_log("Heartbeat sent.", "SUCCESS")
        except Exception as e:
            RF.print_log(f"Heartbeat failed: {e}", "ERROR")
    
    # Optional: stdout heartbeat (always log, even if Telegram disabled)
    RF.print_log(
        f"HB | {crumbs.get('config_hash16','??')} · {crumbs.get('price_common_date','????-??-??')} · "
        f"{crumbs.get('exec_long','')}/{crumbs.get('exec_short','')} · {crumbs.get('run_duration_sec',0):.2f}s · "
        f"{'no-op '+str(crumbs.get('no_op_reason','')) if crumbs.get('no_op') else 'active'}",
        "INFO"
    )

    # Update result breadcrumbs with config hash
    result["breadcrumbs"] = crumbs
    
    # Release run lock before returning
    release_run_lock()

    # Replay pack (one-file snapshot to exactly reproduce a day)
    rep_cfg_rpl = Config(".")._load_yaml("config/reports.yaml") if (Config(".").root / "config/reports.yaml").exists() else {}
    rpl = (rep_cfg_rpl.get("replay_pack") or {})
    if bool(rpl.get("enabled", True)):
        try:
            out_dir = Path(str(rpl.get("out_dir", "replays")))
            tail = int(rpl.get("bars_tail", 5))
            include_prices = bool(rpl.get("include_prices", True))
            
            # assemble minimal symbol package
            symbols_data = {
                LONG:  {"df": long_df,  "last_px": float(last_prices_map.get(LONG, 0.0))},
                SHORT: {"df": short_df, "last_px": float(last_prices_map.get(SHORT, 0.0))}
            }
            
            bundle_path = write_replay_bundle(
                out_dir=out_dir,
                price_common_date=crumbs.get("price_common_date", ""),
                symbols_data=symbols_data,
                context=crumbs,
                positions_before=positions_before,
                intents=[_intent_to_dict(it) for it in intents],
                positions_after=positions_after,
                bars_tail=tail,
                include_prices=include_prices,
            )
            RF.print_log(f"Replay pack written → {bundle_path}", "SUCCESS")
        except Exception as e:
            RF.print_log(f"Replay pack write failed: {e}", "ERROR")

    # --- 13. End of Cycle (Watchdog) ---
    from .guardian.watchdog import touch_heartbeat
    touch_heartbeat(
        regime=crumbs.get('phase', 'UNKNOWN'),
        equity=crumbs.get('equity_now'),
        root=Config().root  # Config singleton has root
    )
    
    # Release run lock before final return
    release_run_lock()

    return result
