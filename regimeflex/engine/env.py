from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

@dataclass(frozen=True)
class Env:
    alpaca_key: str | None  # Paper trading keys
    alpaca_secret: str | None
    alpaca_live_key: str | None  # Live trading keys
    alpaca_live_secret: str | None
    polygon_key: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    env: str

def load_env(dotenv_path: str = ".env") -> Env:
    # Load .env if present, otherwise continue silently.
    if Path(dotenv_path).exists():
        load_dotenv(dotenv_path, override=False)
    return Env(
        alpaca_key=os.getenv("ALPACA_KEY"),
        alpaca_secret=os.getenv("ALPACA_SECRET"),
        alpaca_live_key=os.getenv("ALPACA_LIVE_KEY"),
        alpaca_live_secret=os.getenv("ALPACA_LIVE_SECRET"),
        polygon_key=os.getenv("POLYGON_KEY"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        env=os.getenv("ENV", "dev"),
    )
