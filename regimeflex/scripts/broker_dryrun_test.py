import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import TargetExposure
from engine.exec_planner import plan_orders
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds
from engine.positions import load_positions, set_position
from engine.storage import ENSStyleAudit

def payload_for_audit(p: dict) -> dict:
    # ensure it's JSON-safe & concise
    out = dict(p)
    if "limit_price" in out and out["limit_price"] is None:
        out.pop("limit_price")
    return out

def test_broker_scenario(scenario_name: str, target: TargetExposure, current_positions: dict, minutes_to_close: int):
    RF.print_log(f"\n=== {scenario_name} ===", "INFO")
    
    # Get current price
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])
    
    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares: {target.shares:.2f}  Notional: ${target.dollars:,.2f}", "INFO")
    RF.print_log(f"Current positions: {current_positions}", "INFO")
    RF.print_log(f"Minutes to close: {minutes_to_close}", "INFO")
    
    # Plan intents
    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False,
    )
    
    if not intents:
        RF.print_log("No trade planned — nothing to send to broker.", "SUCCESS")
        return
    
    # Broker executor (DRY-RUN)
    creds = AlpacaCreds(key=None, secret=None)   # placeholders for now
    exe = AlpacaExecutor(creds, dry_run=True)
    payloads = exe.place_orders(intents)
    
    # Audit ORDER records
    audit = ENSStyleAudit()
    for p in payloads:
        rec = audit.log(kind="ORDER", data=payload_for_audit(p))
        RF.print_log(f"ORDER logged → {rec.tx_hash} (block {rec.block})", "SUCCESS")

if __name__ == "__main__":
    RF.print_log("=== Broker Dry-Run Integration Test ===", "INFO")
    
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
    
    # Scenario 1: QQQ LONG target, 40 min to close (limit order)
    target1 = TargetExposure(
        symbol="QQQ",
        direction="LONG", 
        dollars=20 * qqq_price,  # 20 shares worth
        shares=20.0,
        notes="Broker test: increase QQQ position"
    )
    test_broker_scenario("QQQ LONG (limit order)", target1, current_positions, 40)
    
    # Scenario 2: Same target but 10 min to close (MOC order)
    test_broker_scenario("QQQ LONG (MOC order)", target1, current_positions, 10)
    
    # Scenario 3: PSQ LONG target (inverse ETF)
    target2 = TargetExposure(
        symbol="PSQ",
        direction="LONG",
        dollars=8000.0, 
        shares=500.0,  # 8000 / 16.25 ≈ 500
        notes="Broker test: PSQ long position"
    )
    test_broker_scenario("PSQ LONG (inverse ETF)", target2, current_positions, 40)
    
    # Scenario 4: Position reduction (sell order)
    target3 = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=3 * qqq_price,  # Reduce to 3 shares
        shares=3.0,
        notes="Broker test: reduce QQQ position"
    )
    test_broker_scenario("Position reduction (sell)", target3, current_positions, 40)
    
    RF.print_log("\nBroker dry-run integration test OK ✅", "SUCCESS")
