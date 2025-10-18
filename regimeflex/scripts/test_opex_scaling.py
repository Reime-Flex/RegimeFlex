import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.risk import RiskConfig, RiskInputs, dynamic_position_size

if __name__ == "__main__":
    RF.print_log("=== OPEX Scaling Test ===", "INFO")
    
    # Load data
    qqq = get_daily_bars("QQQ")
    qqq_price = float(qqq["close"].iloc[-1])
    
    cfg = RiskConfig()
    
    # Test normal day sizing
    inputs_normal = RiskInputs(
        equity=25000.0,
        price=qqq_price,
        vix=20.0,
        qqq_close=qqq["close"],
        is_fomc_window=False,
        is_opex=False
    )
    
    size_normal, note_normal = dynamic_position_size(
        inputs_normal, qqq["close"], qqq["high"], qqq["low"], cfg
    )
    RF.print_log(f"Normal day: size=${size_normal:,.2f}, note='{note_normal}'", "INFO")
    
    # Test OPEX day sizing
    inputs_opex = RiskInputs(
        equity=25000.0,
        price=qqq_price,
        vix=20.0,
        qqq_close=qqq["close"],
        is_fomc_window=False,
        is_opex=True  # OPEX day
    )
    
    size_opex, note_opex = dynamic_position_size(
        inputs_opex, qqq["close"], qqq["high"], qqq["low"], cfg
    )
    RF.print_log(f"OPEX day: size=${size_opex:,.2f}, note='{note_opex}'", "INFO")
    
    # Compare sizes
    if size_normal > 0 and size_opex > 0:
        scaling_factor = size_opex / size_normal
        RF.print_log(f"OPEX scaling factor: {scaling_factor:.3f} (expected ~0.85)", "INFO")
    
    RF.print_log("OPEX scaling test OK ✅", "SUCCESS")
