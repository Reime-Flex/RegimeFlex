import sys
from pathlib import Path
from datetime import date

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.calendar import is_fomc_blackout, is_opex

if __name__ == "__main__":
    today = date.today()
    cfg = Config(".")
    sched = cfg.schedule or {}

    fomc_dates = sched.get("fomc_dates", [])
    window = tuple(sched.get("fomc_blackout_window", [-1, 1]))
    opex_overrides = sched.get("opex_overrides", [])

    RF.print_log(f"Today: {today.isoformat()}", "INFO")
    RF.print_log(f"FOMC blackout? {is_fomc_blackout(today, fomc_dates, window)}", "RISK")
    RF.print_log(f"OPEX day? {is_opex(today, opex_overrides)}", "RISK")
    RF.print_log("Calendar guard demo OK ✅", "SUCCESS")
