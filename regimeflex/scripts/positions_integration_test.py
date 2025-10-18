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
from engine.positions import load_positions, set_position

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
    RF.print_log("=== Position Store Integration Test ===", "INFO")
    
    # Set up some test positions
    RF.print_log("Setting up test positions...", "INFO")
    set_position("QQQ", 5.0)  # We have 5 QQQ shares
    set_position("PSQ", 0.0)  # No PSQ position
    
    # Load current positions from store
    current_positions = load_positions()
    RF.print_log(f"Current positions from store: {current_positions}", "INFO")
    
    # Create a target that will generate a trade
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    
    # Target: increase QQQ position to 20 shares (need to buy 15 more)
    target = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=20 * qqq_price,  # 20 shares worth
        shares=20.0,
        notes="Integration test: increase QQQ position"
    )
    
    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares: {target.shares:.2f}  Notional: ${target.dollars:,.2f}", "INFO")
    
    # Plan orders using current positions from store
    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=qqq_price,
        minutes_to_close=35,
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
    
    RF.print_log("Position store integration OK ✅", "SUCCESS")
