import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta, timezone

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import seed_cache, get_daily_bars

def make_mock_series(n_days=30, start_price=400.0):
    today = datetime.now(timezone.utc).date()
    dates = pd.date_range(end=today, periods=n_days, freq="B")  # business days
    prices = []
    p = start_price
    for _ in range(len(dates)):
        p *= (1 + 0.002)  # gentle drift
        prices.append(round(p, 2))
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [x * 1.003 for x in prices],
            "low":  [x * 0.997 for x in prices],
            "close": prices,
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )
    return df

if __name__ == "__main__":
    RF.print_log("Seeding mock QQQ and PSQ data into cache…", "INFO")
    qqq = make_mock_series(n_days=40, start_price=400.0)
    psq = make_mock_series(n_days=40, start_price=15.0)
    seed_cache("QQQ", qqq)
    seed_cache("PSQ", psq)
    RF.print_log("Seed complete. Running validations…", "INFO")

    for sym in ("QQQ", "PSQ"):
        df = get_daily_bars(sym)
        RF.print_log(f"{sym}: rows={len(df)}, last={df.index[-1].date()}, close={df['close'].iloc[-1]}", "SUCCESS")

    RF.print_log("Data module skeleton OK ✅", "SUCCESS")
