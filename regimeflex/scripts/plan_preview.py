import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig
from engine.exec_planner import plan_orders

if __name__ == "__main__":
    # 1) Inputs
    equity = 25_000.0
    vix = 20.0
    minutes_to_close = 45   # try 10 to see MOC behavior

    # 2) Load data + compute target
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    cfg = RiskConfig()
    target = compute_target_exposure(qqq=qqq, psq=psq, equity=equity, vix=vix, cfg=cfg)

    # 3) Mock current positions (try changing these)
    current_positions = {
        "QQQ": 0.0,
        "PSQ": 0.0
    }
    price = float((qqq if target.symbol == "QQQ" else psq)["close"].iloc[-1])

    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Desired shares (signed): {target.shares:.2f}", "INFO")
    RF.print_log(f"Minutes to close: {minutes_to_close}", "INFO")

    intents = plan_orders(
        current_positions=current_positions,
        target=target,
        current_price=price,
        minutes_to_close=minutes_to_close,
        min_trade_value=200.0,
        emergency_override=False
    )

    if not intents:
        RF.print_log("No trade planned (below threshold or FLAT).", "SUCCESS")
    else:
        for it in intents:
            RF.print_log(
                f"PLAN → {it.symbol} {it.side} {it.qty:.2f} @ {it.order_type}"
                + (f" lim≈{it.limit_price}" if it.limit_price is not None else "")
                + f" tif={it.time_in_force} | {it.reason}",
                "SIGNAL"
            )

    RF.print_log("Order planner skeleton OK ✅", "SUCCESS")
