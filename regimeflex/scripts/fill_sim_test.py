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

def test_fill_scenario(scenario_name: str, target: TargetExposure, current_positions: dict, minutes_to_close: int):
    RF.print_log(f"\n=== {scenario_name} ===", "INFO")
    
    # Get current price
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])
    
    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares: {target.shares:.2f}  Notional: ${target.dollars:,.2f}", "INFO")
    RF.print_log(f"Positions BEFORE: {current_positions}", "INFO")
    
    # Plan
    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False,
    )
    
    if not intents:
        RF.print_log("No trade planned — skipping scenario.", "SUCCESS")
        return
    
    # Dry-run payloads (for visibility; still not calling network)
    exe = AlpacaExecutor(AlpacaCreds(key=None, secret=None), dry_run=True)
    payloads = exe.place_orders(intents)
    
    # Simulate fills
    fills = simulate_fills(intents, last_price=price)
    for f in fills:
        RF.print_log(f"FILL (sim) → {f.symbol} {f.side} {f.qty:.2f} @ {f.price:.2f} ({f.note})", "SUCCESS")
    
    # Update positions
    positions_after = apply_simulated_fills(current_positions, fills)
    save_positions(positions_after)
    
    RF.print_log(f"Positions AFTER:  {positions_after}", "INFO")
    
    # Audit FILL records
    audit = ENSStyleAudit()
    for f in fills:
        rec = audit.log(kind="FILL", data={
            "symbol": f.symbol,
            "side": f.side,
            "qty": round(float(f.qty), 6),
            "price": float(f.price),
            "note": f.note
        })
        RF.print_log(f"FILL logged → {rec.tx_hash} (block {rec.block})", "SUCCESS")

if __name__ == "__main__":
    RF.print_log("=== Fill Simulation Integration Test ===", "INFO")
    
    # Set up test positions
    RF.print_log("Setting up test positions...", "INFO")
    set_position("QQQ", 5.0)  # We have 5 QQQ shares
    set_position("PSQ", 0.0)  # No PSQ position
    
    # Load current positions from store
    current_positions = load_positions()
    
    # Test scenarios with mock targets that will generate trades
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    psq_price = float(psq["close"].iloc[-1])
    
    # Scenario 1: QQQ LONG target, 25 min to close (limit order)
    target1 = TargetExposure(
        symbol="QQQ",
        direction="LONG", 
        dollars=20 * qqq_price,  # 20 shares worth
        shares=20.0,
        notes="Fill test: increase QQQ position"
    )
    test_fill_scenario("QQQ LONG (limit order)", target1, current_positions, 25)
    
    # Update positions for next scenario
    current_positions = load_positions()
    
    # Scenario 2: Same target but 10 min to close (MOC order)
    target2 = TargetExposure(
        symbol="QQQ",
        direction="LONG", 
        dollars=25 * qqq_price,  # 25 shares worth
        shares=25.0,
        notes="Fill test: further increase QQQ position"
    )
    test_fill_scenario("QQQ LONG (MOC order)", target2, current_positions, 10)
    
    # Update positions for next scenario
    current_positions = load_positions()
    
    # Scenario 3: Position reduction (sell order)
    target3 = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=10 * qqq_price,  # Reduce to 10 shares
        shares=10.0,
        notes="Fill test: reduce QQQ position"
    )
    test_fill_scenario("Position reduction (sell)", target3, current_positions, 25)
    
    RF.print_log("\nFill simulation integration test OK ✅", "SUCCESS")
