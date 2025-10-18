import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.indicators import sma, atr, realized_vol_pct_change, zscore

if __name__ == "__main__":
    RF.print_log("Loading QQQ from cache…", "INFO")
    qqq = get_daily_bars("QQQ")
    close = qqq["close"]
    high, low = qqq["high"], qqq["low"]

    RF.print_log("Computing SMA(20), SMA(50), ATR(14), RVOL(20), Z(20)…", "INFO")
    s20 = sma(close, 20)
    s50 = sma(close, 50)
    a14 = atr(high, low, close, 14)
    rvol20 = realized_vol_pct_change(close, 20)
    z20 = zscore(close, 20)

    # Print the last available values
    RF.print_log(f"SMA20={s20.dropna().iloc[-1]:.4f}", "SUCCESS")
    RF.print_log(f"SMA50={s50.dropna().iloc[-1] if s50.dropna().size else float('nan'):.4f}", "SUCCESS")
    RF.print_log(f"ATR14={a14.dropna().iloc[-1]:.4f}", "SUCCESS")
    RF.print_log(f"RVOL20={rvol20.dropna().iloc[-1]:.4f}", "SUCCESS")
    RF.print_log(f"Z20={z20.dropna().iloc[-1]:.4f}", "SUCCESS")
