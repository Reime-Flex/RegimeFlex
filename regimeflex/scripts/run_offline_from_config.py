import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.runner import run_daily_offline
from engine.report import write_daily_html
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds

if __name__ == "__main__":
    cfg = Config(".")
    run = cfg.run or {}
    tele = cfg.telemetry or {}

    equity = float(run.get("equity", 25_000.0))
    vix = run.get("vix_assumption", 20.0)
    mtc = int(run.get("minutes_to_close", 28))
    min_trade_value = float(run.get("min_trade_value", 200.0))

    RF.print_log(f"Config params: equity={equity}, vix={vix}, mtc={mtc}, min=${min_trade_value}", "INFO")
    result = run_daily_offline(
        equity=equity,
        vix=vix if vix is None or isinstance(vix, (int, float)) else 20.0,
        minutes_to_close=mtc,
        min_trade_value=min_trade_value,
    )

    # HTML report
    rep_cfg = run.get("report", {}) or {}
    if rep_cfg.get("enabled", True):
        out_path = write_daily_html(
            result,
            out_dir=rep_cfg.get("out_dir", "reports"),
            filename_prefix=rep_cfg.get("filename_prefix", "daily_report"),
        )
        RF.print_log(f"HTML report saved → {out_path}", "SUCCESS")

    # Optional Telegram (uses Step 20 gating)
    if (cfg.telemetry or {}).get("enabled", True):
        e = load_env()
        notifier = Notifier(TGCreds(token=e.telegram_bot_token, chat_id=e.telegram_chat_id))
        verbosity = (cfg.telemetry or {}).get("verbosity", "brief")
        notifier.send(Notifier.format_run_summary(result, verbosity=verbosity))
    else:
        RF.print_log("Telemetry disabled by telemetry.yaml", "INFO")
