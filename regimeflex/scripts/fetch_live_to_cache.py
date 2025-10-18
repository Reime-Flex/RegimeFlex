import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.data import get_daily_bars_with_provider

if __name__ == "__main__":
    cfg = Config(".")._load_yaml("config/data.yaml")
    symbols = cfg.get("symbols", ["QQQ","PSQ"])
    RF.print_log(f"Provider: {cfg.get('provider','cache')} | Symbols: {symbols}", "INFO")
    ok = 0
    for sym in symbols:
        try:
            df = get_daily_bars_with_provider(sym, force_refresh=cfg.get("force_refresh", False))
            RF.print_log(f"{sym}: last={df.index[-1].date()} rows={len(df)}", "SUCCESS")
            ok += 1
        except Exception as e:
            RF.print_log(f"{sym}: fetch failed → {e}", "ERROR")
    RF.print_log(f"Completed. Success {ok}/{len(symbols)}", "SUCCESS" if ok==len(symbols) else "RISK")
