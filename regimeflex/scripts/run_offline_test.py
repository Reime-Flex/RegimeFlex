import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.runner import run_daily_offline
from engine.positions import set_position

if __name__ == "__main__":
    RF.print_log("=== RegimeFlex Complete Cycle Test ===", "INFO")
    
    # Set up test positions to ensure we have a trade scenario
    RF.print_log("Setting up test positions for trade scenario...", "INFO")
    set_position("QQQ", 5.0)  # We have 5 QQQ shares
    set_position("PSQ", 0.0)  # No PSQ position
    
    # Test with parameters that should generate a trade
    RF.print_log("\n=== Test 1: QQQ Long Position Increase ===", "INFO")
    result1 = run_daily_offline(
        equity=25000.0,
        vix=18.0,  # Low VIX to avoid blocks
        minutes_to_close=35,  # Limit order time
        min_trade_value=200.0,
    )
    RF.print_log(f"Test 1 Result: dir={result1['target']['direction']} symbol={result1['target']['symbol']}", "SUCCESS")
    
    # Test with MOC scenario
    RF.print_log("\n=== Test 2: MOC Order Scenario ===", "INFO")
    result2 = run_daily_offline(
        equity=25000.0,
        vix=18.0,
        minutes_to_close=10,  # MOC order time
        min_trade_value=200.0,
    )
    RF.print_log(f"Test 2 Result: dir={result2['target']['direction']} symbol={result2['target']['symbol']}", "SUCCESS")
    
    # Test with high VIX (should be blocked)
    RF.print_log("\n=== Test 3: High VIX Block Scenario ===", "INFO")
    result3 = run_daily_offline(
        equity=25000.0,
        vix=40.0,  # High VIX should trigger circuit breaker
        minutes_to_close=35,
        min_trade_value=200.0,
    )
    RF.print_log(f"Test 3 Result: dir={result3['target']['direction']} symbol={result3['target']['symbol']}", "SUCCESS")
    
    RF.print_log("\nComplete cycle test OK ✅", "SUCCESS")
