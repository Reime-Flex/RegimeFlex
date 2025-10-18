import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import compute_target_exposure
from engine.risk import RiskConfig

if __name__ == "__main__":
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    cfg = RiskConfig()
    target = compute_target_exposure(
        qqq=qqq,
        psq=psq,
        equity=25_000.0,
        vix=20.0,
        cfg=cfg
    )

    RF.print_log(f"Target → {target.symbol} | {target.direction}", "SIGNAL")
    RF.print_log(f"Notional: ${target.dollars:,.2f}", "INFO")
    RF.print_log(f"Shares: {target.shares:,.2f}", "INFO")
    RF.print_log(f"Notes: {target.notes}", "INFO")
    RF.print_log("Target exposure computation OK ✅", "SUCCESS")
