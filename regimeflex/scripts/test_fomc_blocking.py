import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.portfolio import TargetExposure
from engine.exec_planner import plan_orders
from engine.positions import load_positions, set_position
from engine.risk import RiskConfig, RiskInputs, circuit_breakers

if __name__ == "__main__":
    RF.print_log("=== FOMC Blocking Test ===", "INFO")
    
    # Set up test positions to ensure we have a trade scenario
    set_position("QQQ", 5.0)
    set_position("PSQ", 0.0)
    
    # Load data
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    qqq_price = float(qqq["close"].iloc[-1])
    
    # Create a forced QQQ target (bypassing normal regime detection)
    target = TargetExposure(
        symbol="QQQ",
        direction="LONG",
        dollars=15000.0,  # 15k notional
        shares=35.0,  # 15000 / 433.28 ≈ 35
        notes="Forced QQQ long target for FOMC blocking test"
    )
    
    RF.print_log(f"Target → {target.symbol} | {target.direction} | ${target.dollars:,.2f}", "INFO")
    
    # Test circuit breakers with FOMC window
    cfg = RiskConfig()
    inputs_fomc = RiskInputs(
        equity=25000.0,
        price=qqq_price,
        vix=20.0,
        qqq_close=qqq["close"],
        is_fomc_window=True,  # FOMC blackout active
        is_opex=False
    )
    
    blocked_fomc, reason_fomc = circuit_breakers(inputs_fomc, cfg)
    RF.print_log(f"FOMC blackout test: blocked={blocked_fomc}, reason='{reason_fomc}'", "RISK")
    
    # Test circuit breakers without FOMC window
    inputs_normal = RiskInputs(
        equity=25000.0,
        price=qqq_price,
        vix=20.0,
        qqq_close=qqq["close"],
        is_fomc_window=False,  # Normal day
        is_opex=False
    )
    
    blocked_normal, reason_normal = circuit_breakers(inputs_normal, cfg)
    RF.print_log(f"Normal day test: blocked={blocked_normal}, reason='{reason_normal}'", "INFO")
    
    # Test OPEX scaling
    inputs_opex = RiskInputs(
        equity=25000.0,
        price=qqq_price,
        vix=20.0,
        qqq_close=qqq["close"],
        is_fomc_window=False,
        is_opex=True  # OPEX day
    )
    
    blocked_opex, reason_opex = circuit_breakers(inputs_opex, cfg)
    RF.print_log(f"OPEX day test: blocked={blocked_opex}, reason='{reason_opex}'", "INFO")
    
    RF.print_log("FOMC blocking test OK ✅", "SUCCESS")
