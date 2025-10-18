from itertools import product
import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

def fmt_row(row):
    return (
        f"SMA(5/20/50/100/200) N/A | "
        f"Zlen={row['z_len']:<2} Zbull={row['z_entry_bull']:<4} Zbear={row['z_entry_bear']:<4}  "
        f"Trades={row['trades']:<4}  CAGR={row['cagr']*100:6.2f}%  "
        f"MaxDD={row['maxdd']*100:6.2f}%  Sharpe={row['sharpe']:5.2f}"
    )

if __name__ == "__main__":
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    RF.print_log("Running quick parameter sweep…", "INFO")

    z_lens = [15, 20, 25]
    z_bull_entries = [-1.8, -2.0, -2.2]
    z_bear_entries = [1.8, 2.0, 2.2]

    rows = []
    for zlen, zbull, zbear in product(z_lens, z_bull_entries, z_bear_entries):
        cfg = BTConfig(
            start_cash=25_000.0,
            vix_assumption=None,
            min_trade_value=200.0,
            commission_per_share=0.005,
            fixed_fee_per_trade=0.00,
            slippage_bps=10.0,
            trend_params={},  # keep default trend filters
            mr_params={
                "z_len": zlen,
                "z_entry_bull": zbull,
                "z_exit_bull": 0.0,
                "z_entry_bear": zbear,
                "z_exit_bear": 0.0,
                "vol_confirm_mult": 1.2
            }
        )
        res = run_backtest(qqq, psq, cfg)
        rows.append({
            "z_len": zlen,
            "z_entry_bull": zbull,
            "z_entry_bear": zbear,
            "trades": res.trades,
            "cagr": res.cagr,
            "maxdd": res.max_dd,
            "sharpe": res.sharpe
        })

    # sort by MAR (CAGR / MaxDD) then Sharpe
    rows.sort(key=lambda r: ((r["cagr"] / (r["maxdd"] + 1e-9)), r["sharpe"]), reverse=True)

    RF.print_log("Top 5 configs by MAR then Sharpe:", "SUCCESS")
    for r in rows[:5]:
        print("  - " + fmt_row(r))

    RF.print_log(f"Tried {len(rows)} configs ✅", "SUCCESS")
