import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import TargetExposure
from engine.exec_planner import plan_orders

def test_scenario(scenario_name: str, target: TargetExposure, current_positions: dict, minutes_to_close: int):
    RF.print_log(f"\n=== {scenario_name} ===", "INFO")
    
    # Get current price
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])
    
    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares (signed): {target.shares:.2f}", "INFO")
    RF.print_log(f"Current positions: {current_positions}", "INFO")
    RF.print_log(f"Minutes to close: {minutes_to_close}", "INFO")
    
    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False
    )
    
    if not intents:
        RF.print_log("No trade planned (below threshold or FLAT).", "SUCCESS")
    else:
        for it in intents:
            RF.print_log(
                f"PLAN → {it.symbol} {it.side} {it.qty:.2f} @ {it.order_type}"
                + (f" lim≈{it.limit_price}" if it.limit_price is not None else "")
                + f" tif={it.time_in_force} | {it.reason}",
                "SIGNAL"
            )

if __name__ == "__main__":
    # Test scenarios with mock targets
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    psq_price = float(psq["close"].iloc[-1])
    
    # Scenario 1: QQQ LONG target, no current position, 45 min to close (should be limit order)
    target1 = TargetExposure(
        symbol="QQQ",
        direction="LONG", 
        dollars=12000.0,
        shares=28.0,  # 12000 / 433.28 ≈ 28
        notes="Mock QQQ long target"
    )
    test_scenario("QQQ LONG (limit order)", target1, {"QQQ": 0.0, "PSQ": 0.0}, 45)
    
    # Scenario 2: Same target but 10 min to close (should be MOC)
    test_scenario("QQQ LONG (MOC order)", target1, {"QQQ": 0.0, "PSQ": 0.0}, 10)
    
    # Scenario 3: PSQ LONG target (inverse ETF)
    target2 = TargetExposure(
        symbol="PSQ",
        direction="LONG",
        dollars=8000.0, 
        shares=500.0,  # 8000 / 16.25 ≈ 500
        notes="Mock PSQ long target"
    )
    test_scenario("PSQ LONG (inverse ETF)", target2, {"QQQ": 0.0, "PSQ": 0.0}, 45)
    
    # Scenario 4: Tiny trade (should be filtered out)
    target3 = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=100.0,
        shares=0.2,  # Very small position
        notes="Tiny trade test"
    )
    test_scenario("Tiny trade (filtered)", target3, {"QQQ": 0.0, "PSQ": 0.0}, 45)
    
    RF.print_log("\nOrder planner test scenarios OK ✅", "SUCCESS")
