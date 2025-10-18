import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.env import load_env
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig
from engine.exec_planner import plan_orders
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds, ALPACA_PAPER_URL, ALPACA_LIVE_URL
from engine.positions import load_positions
from engine.storage import ENSStyleAudit

if __name__ == "__main__":
    # Inputs
    equity = 25_000.0
    vix = 20.0
    minutes_to_close = 35
    min_trade_value = 200.0

    # Load broker config
    cfg = Config(".")._load_yaml("config/broker.yaml")
    alp = (cfg.get("alpaca") or {})
    DRY_RUN = bool(alp.get("dry_run", True))
    base_url = ALPACA_PAPER_URL if alp.get("mode","paper") == "paper" else ALPACA_LIVE_URL

    # Data & target
    qqq = get_daily_bars("QQQ")  # if you switched runner import, this uses provider config
    psq = get_daily_bars("PSQ")
    target = compute_target_exposure(qqq, psq, equity=equity, vix=vix, cfg=RiskConfig())

    RF.print_log(f"Target → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")

    current_positions = load_positions()
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])

    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=min_trade_value,
        emergency_override=False,
    )

    if not intents:
        RF.print_log("No trade planned — exiting.", "SUCCESS")
        raise SystemExit(0)

    # Prepare Alpaca executor
    e = load_env()
    creds = AlpacaCreds(key=e.alpaca_key, secret=e.alpaca_secret, base_url=base_url)
    exe = AlpacaExecutor(creds, dry_run=DRY_RUN)

    # Place or dry-run
    results = exe.place_orders(intents)

    # Audit: if DRY-RUN, log ORDER as payload; if live, log API response
    audit = ENSStyleAudit()
    for res in results:
        if DRY_RUN or "error" in res:
            audit.log(kind="ORDER", data=res if isinstance(res, dict) else {"payload": str(res)})
        else:
            audit.log(kind="ORDER", data={
                "id": res.get("id"),
                "symbol": res.get("symbol"),
                "side": res.get("side"),
                "qty": res.get("qty"),
                "type": res.get("type"),
                "tif": res.get("time_in_force"),
                "status": res.get("status"),
                "submitted_at": res.get("submitted_at")
            })

    RF.print_log("Broker place preview done ✅", "SUCCESS")
