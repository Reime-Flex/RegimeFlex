import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.risk import RiskConfig, RiskInputs, dynamic_position_size, circuit_breakers

if __name__ == "__main__":
    qqq = get_daily_bars("QQQ")
    # use QQQ for regime/sizing and pretend we're sizing QQQ exposure
    close, high, low = qqq["close"], qqq["high"], qqq["low"]

    cfg = RiskConfig()
    inputs = RiskInputs(
        equity=25_000.0,
        price=float(close.iloc[-1]),
        vix=22.0,                      # mock VIX
        qqq_close=close,
        is_fomc_window=False,
        is_opex=False
    )

    blocked, reason = circuit_breakers(inputs, cfg)
    if blocked:
        RF.print_log(f"BLOCKED: {reason}", "RISK")
    else:
        RF.print_log(f"Circuit OK: {reason}", "SUCCESS")
        dollars, note = dynamic_position_size(inputs, close, high, low, cfg)
        RF.print_log(f"Target notional: ${dollars:,.2f}  ({note})", "SIGNAL")
        if dollars > 0:
            shares = dollars / inputs.price
            RF.print_log(f"Approx shares @ ${inputs.price:.2f}: {shares:,.0f}", "INFO")

    RF.print_log("Risk/sizing skeleton OK ✅", "SUCCESS")
