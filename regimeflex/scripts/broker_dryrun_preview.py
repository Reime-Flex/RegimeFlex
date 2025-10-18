import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig
from engine.exec_planner import plan_orders
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds
from engine.positions import load_positions
from engine.storage import ENSStyleAudit

def payload_for_audit(p: dict) -> dict:
    # ensure it's JSON-safe & concise
    out = dict(p)
    if "limit_price" in out and out["limit_price"] is None:
        out.pop("limit_price")
    return out

if __name__ == "__main__":
    # 1) Inputs
    equity = 25_000.0
    vix = 20.0
    minutes_to_close = 40  # try 10 for MOC flow

    # 2) Data & target
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    cfg = RiskConfig()
    target = compute_target_exposure(qqq=qqq, psq=psq, equity=equity, vix=vix, cfg=cfg)

    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")

    # 3) Current positions from store
    current_positions = load_positions()
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])

    # 4) Plan intents
    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False,
    )
    if not intents:
        RF.print_log("No trade planned — nothing to send to broker.", "SUCCESS")
        raise SystemExit(0)

    # 5) Broker executor (DRY-RUN)
    creds = AlpacaCreds(key=None, secret=None)   # placeholders for now
    exe = AlpacaExecutor(creds, dry_run=True)
    payloads = exe.place_orders(intents)

    # 6) Audit ORDER records
    audit = ENSStyleAudit()
    for p in payloads:
        rec = audit.log(kind="ORDER", data=payload_for_audit(p))
        RF.print_log(f"ORDER logged → {rec.tx_hash} (block {rec.block})", "SUCCESS")

    RF.print_log("Broker dry-run preview OK ✅", "SUCCESS")
