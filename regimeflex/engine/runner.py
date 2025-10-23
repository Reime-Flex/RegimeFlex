from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from .identity import RegimeFlexIdentity as RF
from .env import load_env
from .config import Config
from .killswitch import is_killed
from .logrotate import rotate_all
from .pnl import snapshot_from_positions, append_snapshot_csv
from .exposure import exposure_allocator, classify_phase
from .guardrails import enforce_exposure_caps
import time
from .versioning import runtime_versions
from .exposure_delta import current_exposure_weights, exposure_delta
from .exposure_reason import compute_exposure_diagnostics, format_plan_reason
from .symbols import resolve_signal_underlier
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
from .telemetry import Notifier, TGCreds
from .data import get_daily_bars
from .risk import RiskConfig
from .portfolio import compute_target_exposure, TargetExposure
from .exec_planner import plan_orders, OrderIntent
from .exec_alpaca import AlpacaCreds, AlpacaExecutor, ALPACA_PAPER_URL, ALPACA_LIVE_URL
from .reconcile import compare_intents_vs_orders
from .positions import load_positions, save_positions
from .fills import simulate_fills, apply_simulated_fills
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
    
    # Track no-op reason for days with zero intents
    noop_reason = None

    # Config fingerprint
    fp = compute_fingerprint(".")
    RF.print_log(f"Config fingerprint: {fp['sha256_16']} ({len(fp['files'])} files)", "INFO")

    # Audit the fingerprint
    audit = ENSStyleAudit()
    audit.log(kind="CFG", data={"hash16": fp["sha256_16"], "hash": fp["sha256"], "files": fp["files"]})

    if is_killed():
        RF.print_log("KILL-SWITCH active — aborting run before any actions", "RISK")
        noop_reason = "KILL_SWITCH"
        duration_sec = round(time.perf_counter() - t0, 3)
        vers = runtime_versions()
        result = {
            "target": {"symbol": "NA", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "KILL"},
            "positions_before": load_positions(),
            "intents": [],
            "positions_after": load_positions(),
            "breadcrumbs": {
                "no_op": True, 
                "no_op_reason": noop_reason, 
                "config_hash16": fp["sha256_16"],
                "run_duration_sec": duration_sec,
                "versions": vers,
            },
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
            
        return result

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
            "breadcrumbs": {
                "no_op": True, 
                "no_op_reason": noop_reason, 
                "eod_guard": why, 
                "config_hash16": fp["sha256_16"],
                "run_duration_sec": duration_sec,
                "versions": vers,
            },
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

    # Resolve execution instruments
    exec_map = resolve_execution_pair()
    LONG  = sym_upper(exec_map["long"])       # "QQQ" or "TQQQ"
    SHORT = sym_upper(exec_map["short"])      # "PSQ" or "SQQQ"
    sides = [LONG, SHORT]

    # Load price refs for sizing/valuations
    long_df  = get_daily_bars(exec_map["long_ref"])
    short_df = get_daily_bars(exec_map["short_ref"])

    # Signal underlier
    sig_sym, sig_df = resolve_signal_underlier()

    # Compute market phase
    exp_cfg = Config(".")._load_yaml("config/exposure.yaml")
    fast = exp_cfg["trend"]["fast_ma"]
    bb_p = exp_cfg["weights"]["bb_period"]
    bb_std = exp_cfg["weights"]["bb_std"]

    phase = classify_phase(sig_df, fast=fast, bb_p=bb_p, bb_std=bb_std)
    RF.print_log(f"Signal phase → {phase}", "INFO")

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


    # Calculate target dollar exposures based on allocator
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

    # Breadcrumbs for telemetry
    crumbs = {
        "vix": vix,
        "fomc_blackout": is_fomc,
        "opex": is_opex_day,
        "target_notes": target.notes,
        "signal_underlier": sig_sym,   # NEW
        "phase": phase,   # NEW
    }

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
        return {
            "target": asdict(target),
            "positions_before": positions_before,
            "intents": [],
            "positions_after": positions_before,
            "breadcrumbs": {**crumbs, "config_hash16": fp["sha256_16"]},
            "config_fingerprint": fp
        }

    # Log PLAN records
    for it in intents:
        audit.log(kind="PLAN", data=_intent_to_dict(it))

    # --- Optional: place with Alpaca if enabled in config ---
    broker_cfg = Config(".")._load_yaml("config/broker.yaml") if (Config(".").root / "config/broker.yaml").exists() else {}
    alp = (broker_cfg.get("alpaca") or {})
    do_broker = bool(alp.get("enabled", True))  # default on, controlled by dry_run anyway
    dry_run_broker = bool(alp.get("dry_run", True))
    base_url = ALPACA_PAPER_URL if (alp.get("mode","paper") == "paper") else ALPACA_LIVE_URL

    env = load_env()
    exe = AlpacaExecutor(AlpacaCreds(key=env.alpaca_key, secret=env.alpaca_secret, base_url=base_url),
                         dry_run=dry_run_broker)

    broker_results = []
    if do_broker and intents:
        RF.print_log(f"Broker path: mode={alp.get('mode','paper')} dry_run={dry_run_broker}", "INFO")
        broker_results = exe.place_orders(intents)
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

    # Simulate fills → update positions → FILL records
    fills = simulate_fills(intents, last_price=price)
    positions_after = apply_simulated_fills(positions_before, fills)
    save_positions(positions_after)
    for f in fills:
        audit.log(kind="FILL", data={
            "symbol": f.symbol, "side": f.side,
            "qty": round(float(f.qty), 6), "price": float(f.price), "note": f.note
        })

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

    return result
