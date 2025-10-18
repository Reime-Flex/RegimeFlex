import sys
from pathlib import Path
from argparse import ArgumentParser

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.runner import run_daily_offline
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds
from engine.config import Config

if __name__ == "__main__":
    ap = ArgumentParser(description="RegimeFlex offline daily cycle")
    ap.add_argument("--equity", type=float, default=25000.0)
    ap.add_argument("--vix", type=float, default=20.0)
    ap.add_argument("--minutes-to-close", type=int, default=35)
    ap.add_argument("--min-trade-value", type=float, default=200.0)
    args = ap.parse_args()

    RF.print_log(
        f"Params: equity={args.equity:.2f}, vix={args.vix:.2f}, mtc={args.minutes_to_close}, min=${args.min_trade_value:.2f}",
        "INFO",
    )
    result = run_daily_offline(
        equity=args.equity,
        vix=args.vix,
        minutes_to_close=args.minutes_to_close,
        min_trade_value=args.min_trade_value,
    )
    RF.print_log(f"Result summary: dir={result['target']['direction']} symbol={result['target']['symbol']}", "SUCCESS")

    # Send summary (dry-run if no creds)
    cfg = Config(".")
    tele = cfg.telemetry or {}
    if tele.get("enabled", True):
        e = load_env()
        notifier = Notifier(TGCreds(token=e.telegram_bot_token, chat_id=e.telegram_chat_id))
        verbosity = tele.get("verbosity", "brief")
        notifier.send(Notifier.format_run_summary(result, verbosity=verbosity))
    else:
        RF.print_log("Telemetry disabled by config/telemetry.yaml", "INFO")
