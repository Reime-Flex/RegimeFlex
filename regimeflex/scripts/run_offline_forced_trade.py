import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import TargetExposure
from engine.exec_planner import plan_orders
from engine.exec_alpaca import AlpacaCreds, AlpacaExecutor
from engine.positions import load_positions, save_positions, set_position
from engine.fills import simulate_fills, apply_simulated_fills
from engine.storage import ENSStyleAudit

def _intent_to_dict(it):
    return {
        "symbol": it.symbol,
        "side": it.side,
        "qty": round(float(it.qty), 6),
        "order_type": it.order_type,
        "time_in_force": it.time_in_force,
        "limit_price": None if it.limit_price is None else float(it.limit_price),
        "reason": it.reason,
    }

def run_forced_trade_cycle():
    RF.print_log("RegimeFlex forced trade cycle starting", "INFO")
    
    # Set up test positions
    set_position("QQQ", 5.0)
    set_position("PSQ", 0.0)
    
    # Load data
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    
    # Create a forced QQQ target (bypassing normal regime detection)
    target = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=15000.0,  # 15k notional
        shares=35.0,  # 15000 / 433.28 ≈ 35
        notes="Forced QQQ long target for testing"
    )
    
    RF.print_log(f"Target → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")
    
    # Positions (before)
    positions_before = load_positions()
    RF.print_log(f"Positions BEFORE: {positions_before}", "INFO")
    
    # Plan intents
    intents = plan_orders(
        current_positions=positions_before,
        target=target,
        current_price=qqq_price,
        minutes_to_close=35,
        min_trade_value=200.0,
        emergency_override=False,
    )
    
    audit = ENSStyleAudit()
    
    if not intents:
        RF.print_log("No trade planned (flat, blocked, or below threshold).", "SUCCESS")
        return
    
    # Log PLAN records
    for it in intents:
        audit.log(kind="PLAN", data=_intent_to_dict(it))
        RF.print_log(f"PLAN logged → {it.symbol} {it.side} {it.qty:.2f} @ {it.order_type}", "SIGNAL")
    
    # Broker dry-run payloads → ORDER records
    exe = AlpacaExecutor(AlpacaCreds(key=None, secret=None), dry_run=True)
    payloads = exe.place_orders(intents)
    for p in payloads:
        audit.log(kind="ORDER", data={k: v for k, v in p.items() if not (k == "limit_price" and v is None)})
        RF.print_log(f"ORDER logged → {p['symbol']} {p['side']} {p['qty']} @ {p['type']}", "SIGNAL")
    
    # Simulate fills → update positions → FILL records
    fills = simulate_fills(intents, last_price=qqq_price)
    positions_after = apply_simulated_fills(positions_before, fills)
    save_positions(positions_after)
    
    for f in fills:
        audit.log(kind="FILL", data={
            "symbol": f.symbol, "side": f.side,
            "qty": round(float(f.qty), 6), "price": float(f.price), "note": f.note
        })
        RF.print_log(f"FILL logged → {f.symbol} {f.side} {f.qty:.2f} @ {f.price:.2f}", "SUCCESS")
    
    RF.print_log(f"Positions AFTER: {positions_after}", "INFO")
    RF.print_log("Forced trade cycle complete", "SUCCESS")

if __name__ == "__main__":
    run_forced_trade_cycle()
