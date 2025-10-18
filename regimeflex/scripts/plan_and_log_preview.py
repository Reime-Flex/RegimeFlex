import sys
from pathlib import Path
from dataclasses import asdict

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig
from engine.exec_planner import plan_orders, OrderIntent
from engine.storage import ENSStyleAudit

def intent_to_dict(it: OrderIntent) -> dict:
    return {
        "symbol": it.symbol,
        "side": it.side,
        "qty": round(float(it.qty), 6),
        "order_type": it.order_type,
        "time_in_force": it.time_in_force,
        "limit_price": None if it.limit_price is None else float(it.limit_price),
        "reason": it.reason,
    }

if __name__ == "__main__":
    # 1) Inputs
    equity = 25_000.0
    vix = 20.0
    minutes_to_close = 35  # try 10 later to see MOC

    # 2) Data & target
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    cfg = RiskConfig()
    target = compute_target_exposure(qqq=qqq, psq=psq, equity=equity, vix=vix, cfg=cfg)

    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares: {target.shares:.2f}  Notional: ${target.dollars:,.2f}", "INFO")

    # 3) Load current positions from store
    from engine.positions import load_positions
    current_positions = load_positions()
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])

    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False,
    )

    if not intents:
        RF.print_log("No trade planned (below threshold, flat, or blocked).", "SUCCESS")
    else:
        audit = ENSStyleAudit()
        for it in intents:
            RF.print_log(
                f"PLAN → {it.symbol} {it.side} {it.qty:.2f} @ {it.order_type}"
                + (f" lim≈{it.limit_price}" if it.limit_price is not None else "")
                + f" tif={it.time_in_force}", "SIGNAL"
            )
            rec = audit.log(kind="PLAN", data=intent_to_dict(it))
            RF.print_log(f"Audit TX → {rec.tx_hash}  (block {rec.block})", "SUCCESS")

    RF.print_log("Planner-to-ledger wiring OK ✅", "SUCCESS")
