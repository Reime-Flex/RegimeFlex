from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from .identity import RegimeFlexIdentity as RF
from .env import load_env
from .config import Config
from .killswitch import is_killed
from .logrotate import rotate_all
from .pnl import snapshot_from_positions, append_snapshot_csv
from .exposure import exposure_allocator
from .guardrails import enforce_exposure_caps
from .timing import eod_ready
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
    RF.print_log("RegimeFlex offline daily cycle starting", "INFO")

    if is_killed():
        RF.print_log("KILL-SWITCH active — aborting run before any actions", "RISK")
        return {
            "target": {"symbol": "NA", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "KILL"},
            "positions_before": {},
            "intents": [],
            "positions_after": {},
            "breadcrumbs": {"kill_switch": True},
            "snapshot": {}
        }

    # EOD timing guard
    ok_time, why = eod_ready(minutes_to_close)
    RF.print_log(f"EOD timing check → {why}", "RISK" if not ok_time else "INFO")
    if not ok_time:
        # Exit cleanly before any actions
        return {
            "target": {"symbol": "NA", "direction": "FLAT", "dollars": 0.0, "shares": 0.0, "notes": "EOD_GUARD"},
            "positions_before": load_positions(),   # optional: show current
            "intents": [],
            "positions_after": load_positions(),
            "breadcrumbs": {"eod_guard": why},
            "snapshot": {}
        }

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

    # Data
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    # Exposure allocation (using QQQ as NDX proxy)
    alloc = exposure_allocator(qqq)
    alloc, guard_note = enforce_exposure_caps(alloc)
    RF.print_log(f"Allocation (guarded) → TQQQ={alloc['TQQQ']:.2f} SQQQ={alloc['SQQQ']:.2f}", "INFO")

    # Calculate target dollar exposures based on allocator
    tqqq_target_dollars = equity * alloc["TQQQ"]
    sqqq_target_dollars = equity * alloc["SQQQ"]
    
    # Determine primary target (largest allocation)
    if tqqq_target_dollars > sqqq_target_dollars:
        target_symbol = "QQQ"  # Use QQQ as TQQQ proxy
        target_dollars = tqqq_target_dollars
        target_direction = "LONG"
    elif sqqq_target_dollars > tqqq_target_dollars:
        target_symbol = "PSQ"  # Use PSQ as SQQQ proxy
        target_dollars = sqqq_target_dollars
        target_direction = "LONG"
    else:
        target_symbol = "QQQ"
        target_dollars = 0.0
        target_direction = "FLAT"

    # Create target exposure
    target_price = float((qqq if target_symbol == "QQQ" else psq)["close"].iloc[-1])
    target_shares = target_dollars / target_price if target_price > 0 else 0.0
    
    target = TargetExposure(
        symbol=target_symbol,
        direction=target_direction,
        dollars=target_dollars,
        shares=target_shares,
        notes=f"Exposure allocator: TQQQ={alloc['TQQQ']:.2f} SQQQ={alloc['SQQQ']:.2f}"
    )
    RF.print_log(f"Target → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")

    # Breadcrumbs for telemetry
    crumbs = {
        "vix": vix,
        "fomc_blackout": is_fomc,
        "opex": is_opex_day,
        "target_notes": target.notes,
    }

    # Positions (before)
    positions_before = load_positions()
    RF.print_log(f"Positions BEFORE: {positions_before}", "INFO")

    # Plan intents
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])
    intents: List[OrderIntent] = plan_orders(
        current_positions=positions_before,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=min_trade_value,
        emergency_override=False,
    )

    audit = ENSStyleAudit()

    if not intents:
        RF.print_log("No trade planned (flat, blocked, or below threshold).", "SUCCESS")
        return {
            "target": asdict(target),
            "positions_before": positions_before,
            "intents": [],
            "positions_after": positions_before,
            "breadcrumbs": crumbs,  # NEW
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

    # Daily PnL/Exposure snapshot
    try:
        equity_ref = float(Config(".").run.get("equity", 25000.0))
    except Exception:
        equity_ref = 25000.0

    # Last prices for valuation
    last_prices = {
        "QQQ": float(qqq["close"].iloc[-1]),
        "PSQ": float(psq["close"].iloc[-1]),
    }

    snap = snapshot_from_positions(positions_after, last_prices, equity_ref)
    append_snapshot_csv(snap)

    # Log rotation at end of daily run (config-gated)
    logs_cfg = Config(".")._load_yaml("config/logs.yaml") if (Config(".").root / "config/logs.yaml").exists() else {}
    if logs_cfg.get("rotate_on_run", True):
        rotate_all()

    return {
        "target": asdict(target),
        "positions_before": positions_before,
        "intents": [_intent_to_dict(it) for it in intents],
        "positions_after": positions_after,
        "breadcrumbs": crumbs,  # NEW
        "snapshot": snap,  # NEW
    }
