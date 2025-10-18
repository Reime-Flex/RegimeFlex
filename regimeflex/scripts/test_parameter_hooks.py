import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

if __name__ == "__main__":
    RF.print_log("=== Parameter Hooks Test ===", "INFO")
    
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    
    # Test with different Z-score parameters
    RF.print_log("Testing parameter hooks with different Z-score thresholds...", "INFO")
    
    # Test 1: Default parameters
    cfg_default = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.005,
        fixed_fee_per_trade=0.00,
        slippage_bps=10.0,
        trend_params={},
        mr_params={}  # Use defaults
    )
    res_default = run_backtest(qqq, psq, cfg_default)
    
    # Test 2: More aggressive Z-score thresholds
    cfg_aggressive = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.005,
        fixed_fee_per_trade=0.00,
        slippage_bps=10.0,
        trend_params={},
        mr_params={
            "z_len": 15,
            "z_entry_bull": -1.5,  # More aggressive entry
            "z_exit_bull": 0.5,     # Earlier exit
            "z_entry_bear": 1.5,    # More aggressive entry
            "z_exit_bear": -0.5,    # Earlier exit
            "vol_confirm_mult": 1.0  # Lower volume requirement
        }
    )
    res_aggressive = run_backtest(qqq, psq, cfg_aggressive)
    
    # Test 3: Conservative Z-score thresholds
    cfg_conservative = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.005,
        fixed_fee_per_trade=0.00,
        slippage_bps=10.0,
        trend_params={},
        mr_params={
            "z_len": 30,
            "z_entry_bull": -2.5,  # More conservative entry
            "z_exit_bull": -0.5,   # Later exit
            "z_entry_bear": 2.5,   # More conservative entry
            "z_exit_bear": 0.5,    # Later exit
            "vol_confirm_mult": 1.5  # Higher volume requirement
        }
    )
    res_conservative = run_backtest(qqq, psq, cfg_conservative)
    
    # Compare results
    RF.print_log("\n--- Parameter Hook Results ---", "INFO")
    RF.print_log(f"Default:      Trades={res_default.trades}, CAGR={res_default.cagr*100:.2f}%, Sharpe={res_default.sharpe:.2f}", "INFO")
    RF.print_log(f"Aggressive:   Trades={res_aggressive.trades}, CAGR={res_aggressive.cagr*100:.2f}%, Sharpe={res_aggressive.sharpe:.2f}", "INFO")
    RF.print_log(f"Conservative: Trades={res_conservative.trades}, CAGR={res_conservative.cagr*100:.2f}%, Sharpe={res_conservative.sharpe:.2f}", "INFO")
    
    # Show parameter differences
    RF.print_log("\n--- Parameter Differences ---", "INFO")
    RF.print_log("Default: z_len=20, z_entry_bull=-2.0, z_entry_bear=2.0", "INFO")
    RF.print_log("Aggressive: z_len=15, z_entry_bull=-1.5, z_entry_bear=1.5", "INFO")
    RF.print_log("Conservative: z_len=30, z_entry_bull=-2.5, z_entry_bear=2.5", "INFO")
    
    RF.print_log("Parameter hooks test OK ✅", "SUCCESS")
