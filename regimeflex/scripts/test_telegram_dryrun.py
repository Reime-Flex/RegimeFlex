import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.telemetry import Notifier, TGCreds

if __name__ == "__main__":
    RF.print_log("=== Telegram Dry-Run Test ===", "INFO")
    
    # Test with no credentials (should dry-run)
    n = Notifier(TGCreds(token=None, chat_id=None))
    msg = "*🧪 RegimeFlex Dry-Run Test*\nThis message should appear in console only."
    RF.print_log("Testing dry-run mode (no credentials)...", "INFO")
    n.send(msg)
    
    # Test with partial credentials (should dry-run)
    n2 = Notifier(TGCreds(token="fake_token", chat_id=None))
    msg2 = "*🧪 RegimeFlex Partial Creds Test*\nThis should also dry-run."
    RF.print_log("Testing with partial credentials...", "INFO")
    n2.send(msg2)
    
    RF.print_log("Telegram dry-run test OK ✅", "SUCCESS")
