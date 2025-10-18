import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig
from engine.exec_planner import plan_orders
from engine.exec_alpaca import AlpacaCreds, AlpacaExecutor
from engine.positions import load_positions, save_positions
from engine.fills import simulate_fills, apply_simulated_fills
from engine.storage import ENSStyleAudit

if __name__ == "__main__":
    # Inputs
    equity = 25_000.0
    vix = 20.0
    minutes_to_close = 25   # try >30 for limit flow, <=30 for MOC flow

    # Data & target
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    price = float(qqq["close"].iloc[-1])  # use QQQ last for sim; OK for demo
    cfg = RiskConfig()
    target = compute_target_exposure(qqq=qqq, psq=psq, equity=equity, vix=vix, cfg=cfg)

    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")

    # Positions before
    positions_before = load_positions()
    RF.print_log(f"Positions BEFORE: {positions_before}", "INFO")

    # Plan
    intents = plan_orders(
        current_positions=positions_before,
        target=target,
        current_price=price if target.symbol == "QQQ" else float(psq['close'].iloc[-1]),
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False,
    )
    if not intents:
        RF.print_log("No trade planned — exiting.", "SUCCESS")
        raise SystemExit(0)

    # Dry-run payloads (for visibility; still not calling network)
    exe = AlpacaExecutor(AlpacaCreds(key=None, secret=None), dry_run=True)
    payloads = exe.place_orders(intents)

    # Simulate fills
    fills = simulate_fills(intents, last_price=price if target.symbol == "QQQ" else float(psq['close'].iloc[-1]))
    for f in fills:
        RF.print_log(f"FILL (sim) → {f.symbol} {f.side} {f.qty:.2f} @ {f.price:.2f} ({f.note})", "SUCCESS")

    # Update positions
    positions_after = apply_simulated_fills(positions_before, fills)
    save_positions(positions_after)

    RF.print_log(f"Positions AFTER:  {positions_after}", "INFO")

    # Audit FILL records
    audit = ENSStyleAudit()
    for f in fills:
        rec = audit.log(kind="FILL", data={
            "symbol": f.symbol,
            "side": f.side,
            "qty": round(float(f.qty), 6),
            "price": float(f.price),
            "note": f.note
        })
        RF.print_log(f"FILL logged → {rec.tx_hash} (block {rec.block})", "SUCCESS")

    RF.print_log("Fill simulator + position update OK ✅", "SUCCESS")
