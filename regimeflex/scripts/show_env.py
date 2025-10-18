import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.env import load_env

if __name__ == "__main__":
    RF.print_log("Loading environment…", "INFO")
    e = load_env()
    RF.print_log(f"ENV: {e.env}", "INFO")
    # Show only whether keys exist, never their contents
    RF.print_log(f"ALPACA_PAPER set? {'yes' if (e.alpaca_key and e.alpaca_secret) else 'no'}", "SUCCESS")
    RF.print_log(f"ALPACA_LIVE set? {'yes' if (e.alpaca_live_key and e.alpaca_live_secret) else 'no'}", "SUCCESS")
    RF.print_log(f"POLYGON_KEY set? {'yes' if e.polygon_key else 'no'}", "SUCCESS")
    RF.print_log(f"TELEGRAM creds set? {'yes' if (e.telegram_bot_token and e.telegram_chat_id) else 'no'}", "SUCCESS")
    RF.print_log("Env load OK ✅", "SUCCESS")
