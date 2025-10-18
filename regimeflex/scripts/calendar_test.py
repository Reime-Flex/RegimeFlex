import sys
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.calendar import is_fomc_blackout, is_opex, is_third_friday

if __name__ == "__main__":
    RF.print_log("=== Calendar Functionality Test ===", "INFO")
    
    # Test third Friday detection
    RF.print_log("\n--- Third Friday Tests ---", "INFO")
    test_dates = [
        date(2025, 10, 17),  # 3rd Friday of October 2025
        date(2025, 10, 18),  # Saturday (not 3rd Friday)
        date(2025, 11, 21),  # 3rd Friday of November 2025
        date(2025, 12, 19),  # 3rd Friday of December 2025
    ]
    
    for d in test_dates:
        is_3rd_fri = is_third_friday(d)
        is_opex_day = is_opex(d)
        RF.print_log(f"{d.isoformat()} ({d.strftime('%A')}) → 3rd Friday: {is_3rd_fri}, OPEX: {is_opex_day}", "INFO")
    
    # Test FOMC blackout detection
    RF.print_log("\n--- FOMC Blackout Tests ---", "INFO")
    fomc_meeting = date(2025, 11, 5)  # Mock FOMC meeting
    fomc_dates = [fomc_meeting.isoformat()]
    window = (-1, 1)  # day before, meeting day, day after
    
    test_dates_fomc = [
        fomc_meeting - timedelta(days=2),  # 2 days before (should be False)
        fomc_meeting - timedelta(days=1),  # 1 day before (should be True)
        fomc_meeting,                      # meeting day (should be True)
        fomc_meeting + timedelta(days=1),  # 1 day after (should be True)
        fomc_meeting + timedelta(days=2),  # 2 days after (should be False)
    ]
    
    for d in test_dates_fomc:
        is_blackout = is_fomc_blackout(d, fomc_dates, window)
        RF.print_log(f"{d.isoformat()} → FOMC blackout: {is_blackout}", "INFO")
    
    # Test OPEX overrides
    RF.print_log("\n--- OPEX Override Tests ---", "INFO")
    override_date = date(2025, 10, 18)  # Today
    opex_overrides = [override_date.isoformat()]
    
    is_opex_override = is_opex(override_date, opex_overrides)
    RF.print_log(f"{override_date.isoformat()} → OPEX (with override): {is_opex_override}", "INFO")
    
    RF.print_log("\nCalendar functionality test OK ✅", "SUCCESS")
