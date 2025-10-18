import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

if __name__ == "__main__":
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    RF.print_log("Running quick backtest (with frictions)…", "INFO")
    cfg = BTConfig(
        start_cash=25_000.0,
        vix_assumption=None,
        min_trade_value=200.0,
        commission_per_share=0.005,  # 0.5¢ per share
        fixed_fee_per_trade=0.00,
        slippage_bps=10.0            # 10 bps
    )
    res = run_backtest(qqq, psq, cfg)

    RF.print_log(f"Trades: {res.trades}", "INFO")
    RF.print_log(f"CAGR:   {res.cagr*100:.2f}%", "SUCCESS")
    RF.print_log(f"Max DD: {res.max_dd*100:.2f}%", "RISK")
    RF.print_log(f"Sharpe: {res.sharpe:.2f}", "INFO")
    RF.print_log(f"Equity curve points: {len(res.equity_curve)}", "INFO")
    RF.print_log("Backtest with frictions OK ✅", "SUCCESS")
