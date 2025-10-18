import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.telemetry import Notifier

if __name__ == "__main__":
    RF.print_log("=== Telemetry Verbosity Test ===", "INFO")
    
    # Test the formatted run summary with different verbosity levels
    test_result = {
        "target": {
            "direction": "LONG",
            "symbol": "QQQ",
            "dollars": 15000.0,
            "shares": 35.0
        },
        "intents": [
            {"symbol": "QQQ", "side": "BUY", "qty": 30.0, "order_type": "limit"}
        ],
        "positions_after": {"QQQ": 35.0, "PSQ": 0.0},
        "breadcrumbs": {
            "vix": 22.5,
            "fomc_blackout": False,
            "opex": True,
            "target_notes": "Trend following signal with regime confirmation"
        }
    }
    
    # Test brief mode
    RF.print_log("\n--- Brief Mode ---", "INFO")
    brief_msg = Notifier.format_run_summary(test_result, verbosity="brief")
    RF.print_log(brief_msg, "INFO")
    
    # Test full mode
    RF.print_log("\n--- Full Mode ---", "INFO")
    full_msg = Notifier.format_run_summary(test_result, verbosity="full")
    RF.print_log(full_msg, "INFO")
    
    RF.print_log("\nTelemetry verbosity test OK ✅", "SUCCESS")
