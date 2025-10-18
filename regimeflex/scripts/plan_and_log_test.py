import sys
from pathlib import Path
from dataclasses import asdict

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import TargetExposure
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

def test_plan_and_log(scenario_name: str, target: TargetExposure, current_positions: dict, minutes_to_close: int):
    RF.print_log(f"\n=== {scenario_name} ===", "INFO")
    
    # Get current price
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])
    
    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares: {target.shares:.2f}  Notional: ${target.dollars:,.2f}", "INFO")
    RF.print_log(f"Current positions: {current_positions}", "INFO")
    RF.print_log(f"Minutes to close: {minutes_to_close}", "INFO")
    
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

if __name__ == "__main__":
    # Test scenarios with mock targets that will generate trades
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    psq_price = float(psq["close"].iloc[-1])
    
    # Scenario 1: QQQ LONG target, no current position, 35 min to close (limit order)
    target1 = TargetExposure(
        symbol="QQQ",
        direction="LONG", 
        dollars=12000.0,
        shares=28.0,  # 12000 / 433.28 ≈ 28
        notes="Mock QQQ long target for planner-ledger test"
    )
    test_plan_and_log("QQQ LONG (limit order)", target1, {"QQQ": 0.0, "PSQ": 0.0}, 35)
    
    # Scenario 2: Same target but 10 min to close (MOC order)
    test_plan_and_log("QQQ LONG (MOC order)", target1, {"QQQ": 0.0, "PSQ": 0.0}, 10)
    
    # Scenario 3: PSQ LONG target (inverse ETF)
    target2 = TargetExposure(
        symbol="PSQ",
        direction="LONG",
        dollars=8000.0, 
        shares=500.0,  # 8000 / 16.25 ≈ 500
        notes="Mock PSQ long target for planner-ledger test"
    )
    test_plan_and_log("PSQ LONG (inverse ETF)", target2, {"QQQ": 0.0, "PSQ": 0.0}, 35)
    
    # Scenario 4: Position adjustment (reducing position)
    target3 = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=6000.0,
        shares=14.0,  # Half the position
        notes="Position reduction test"
    )
    test_plan_and_log("Position reduction", target3, {"QQQ": 28.0, "PSQ": 0.0}, 35)
    
    RF.print_log("\nPlanner-to-ledger wiring test OK ✅", "SUCCESS")
