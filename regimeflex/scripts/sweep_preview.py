from itertools import product
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import sys

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.backtest import run_backtest, BTConfig

REPORTS = Path("reports")
REPORTS.mkdir(parents=True, exist_ok=True)

def run_grid():
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    RF.print_log("Running parameter sweep…", "INFO")

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
            trend_params={},  # keep defaults
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

    df = pd.DataFrame(rows)
    df["mar"] = df["cagr"] / (df["maxdd"].replace(0, 1e-9))
    return df

def save_csv(df: pd.DataFrame, name: str = "sweep_results.csv"):
    path = REPORTS / name
    df.to_csv(path, index=False)
    RF.print_log(f"CSV saved → {path}", "SUCCESS")

def plot_scatter(df: pd.DataFrame, name: str = "sweep_scatter_mar.png"):
    # MAR vs Sharpe, point size ~ trades, label by (z_len, z_bull, z_bear)
    fig = plt.figure(figsize=(7,5))
    s = (df["trades"].clip(lower=1) ** 0.8) * 10
    plt.scatter(df["mar"], df["sharpe"], s=s)
    plt.xlabel("MAR (CAGR / MaxDD)")
    plt.ylabel("Sharpe")
    plt.title("RegimeFlex MR Param Sweep — MAR vs Sharpe")
    fig.tight_layout()
    out = REPORTS / name
    fig.savefig(out, dpi=120)
    plt.close(fig)
    RF.print_log(f"Scatter saved → {out}", "SUCCESS")

def plot_pivot(df: pd.DataFrame, z_bear=2.0, name: str = "sweep_pivot_mar.png"):
    # Heatmap-like pivot of MAR by z_len (rows) x z_entry_bull (cols) at fixed z_entry_bear
    sub = df[df["z_entry_bear"].round(2) == round(z_bear, 2)].copy()
    if sub.empty:
        RF.print_log(f"No rows for z_entry_bear={z_bear}", "RISK")
        return
    pv = sub.pivot(index="z_len", columns="z_entry_bull", values="mar")
    fig = plt.figure(figsize=(7,5))
    im = plt.imshow(pv.values, aspect="auto")
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(pv.shape[1]), [str(c) for c in pv.columns])
    plt.yticks(range(pv.shape[0]), [str(r) for r in pv.index])
    plt.xlabel("z_entry_bull threshold")
    plt.ylabel("z_len")
    plt.title(f"MAR pivot @ z_entry_bear={z_bear}")
    fig.tight_layout()
    out = REPORTS / name
    fig.savefig(out, dpi=120)
    plt.close(fig)
    RF.print_log(f"Pivot saved → {out}", "SUCCESS")

if __name__ == "__main__":
    df = run_grid()
    # Sort & preview top rows
    df_sorted = df.sort_values(by=["mar","sharpe"], ascending=False)
    RF.print_log(f"Top config preview:\n{df_sorted.head(5)}", "INFO")

    save_csv(df_sorted, "sweep_results.csv")
    plot_scatter(df_sorted, "sweep_scatter_mar.png")
    plot_pivot(df_sorted, z_bear=2.0, name="sweep_pivot_mar.png")

    RF.print_log("Sweep export & plots OK ✅", "SUCCESS")
