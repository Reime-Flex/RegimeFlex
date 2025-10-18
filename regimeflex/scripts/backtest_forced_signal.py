import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

if __name__ == "__main__":
    RF.print_log("=== Backtest with Forced Signal Test ===", "INFO")
    
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")
    
    # Test with a very low min trade value to force trades
    RF.print_log("Running backtest with low min trade value...", "INFO")
    res = run_backtest(qqq, psq, BTConfig(
        start_cash=25_000.0, 
        vix_assumption=None,
        min_trade_value=50.0  # Lower threshold
    ))
    
    RF.print_log(f"Trades: {res.trades}", "INFO")
    RF.print_log(f"CAGR:   {res.cagr*100:.2f}%", "SUCCESS")
    RF.print_log(f"Max DD: {res.max_dd*100:.2f}%", "RISK")
    RF.print_log(f"Sharpe: {res.sharpe:.2f}", "INFO")
    RF.print_log(f"Equity curve points: {len(res.equity_curve)}", "INFO")
    
    # Show equity curve stats
    if len(res.equity_curve) > 0:
        RF.print_log(f"Start equity: ${res.equity_curve.iloc[0]:,.2f}", "INFO")
        RF.print_log(f"End equity: ${res.equity_curve.iloc[-1]:,.2f}", "INFO")
        RF.print_log(f"Max equity: ${res.equity_curve.max():,.2f}", "INFO")
        RF.print_log(f"Min equity: ${res.equity_curve.min():,.2f}", "INFO")
    
    RF.print_log("Backtest forced signal test OK ✅", "SUCCESS")
