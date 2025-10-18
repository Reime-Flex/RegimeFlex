import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.telemetry import Notifier, TGCreds

if __name__ == "__main__":
    RF.print_log("=== Telegram Format Test ===", "INFO")
    
    # Test the formatted run summary
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
        "positions_after": {"QQQ": 35.0, "PSQ": 0.0}
    }
    
    formatted_msg = Notifier.format_run_summary(test_result)
    RF.print_log("Formatted message:", "INFO")
    RF.print_log(formatted_msg, "INFO")
    
    # Test sending the formatted message (dry-run)
    n = Notifier(TGCreds(token=None, chat_id=None))
    RF.print_log("Sending formatted message (dry-run)...", "INFO")
    n.send(formatted_msg)
    
    RF.print_log("Telegram format test OK ✅", "SUCCESS")
