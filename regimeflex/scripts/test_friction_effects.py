import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

if __name__ == "__main__":
    RF.print_log("=== Friction Effects Test ===", "INFO")
    
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    
    # Test without frictions
    RF.print_log("Running backtest WITHOUT frictions...", "INFO")
    cfg_no_friction = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.0,
        fixed_fee_per_trade=0.0,
        slippage_bps=0.0
    )
    res_no_friction = run_backtest(qqq, psq, cfg_no_friction)
    
    # Test with frictions
    RF.print_log("Running backtest WITH frictions...", "INFO")
    cfg_with_friction = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.005,  # 0.5¢ per share
        fixed_fee_per_trade=1.0,    # $1 per trade
        slippage_bps=10.0           # 10 bps
    )
    res_with_friction = run_backtest(qqq, psq, cfg_with_friction)
    
    # Compare results
    RF.print_log("\n--- Comparison ---", "INFO")
    RF.print_log(f"Without frictions: Trades={res_no_friction.trades}, CAGR={res_no_friction.cagr*100:.2f}%, Sharpe={res_no_friction.sharpe:.2f}", "INFO")
    RF.print_log(f"With frictions:    Trades={res_with_friction.trades}, CAGR={res_with_friction.cagr*100:.2f}%, Sharpe={res_with_friction.sharpe:.2f}", "INFO")
    
    # Show friction configuration
    RF.print_log("\n--- Friction Configuration ---", "INFO")
    RF.print_log(f"Commission per share: ${cfg_with_friction.commission_per_share:.3f}", "INFO")
    RF.print_log(f"Fixed fee per trade: ${cfg_with_friction.fixed_fee_per_trade:.2f}", "INFO")
    RF.print_log(f"Slippage: {cfg_with_friction.slippage_bps:.1f} bps", "INFO")
    
    RF.print_log("Friction effects test OK ✅", "SUCCESS")
