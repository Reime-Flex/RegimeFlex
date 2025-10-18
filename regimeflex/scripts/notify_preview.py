import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds

if __name__ == "__main__":
    e = load_env()
    n = Notifier(TGCreds(token=e.telegram_bot_token, chat_id=e.telegram_chat_id))
    msg = "*✅ RegimeFlex Telemetry Test*\nThis is a test message from your local environment."
    RF.print_log("Attempting to send Telegram test message…", "INFO")
    n.send(msg)
