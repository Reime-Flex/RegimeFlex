from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class DailyBar:
    date: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int

class DataError(Exception): ...
class ValidationError(DataError): ...

def _cache_path(symbol: str) -> Path:
    safe = symbol.upper().replace("/", "_")
    return CACHE_DIR / f"{safe}.csv"

def save_to_cache(symbol: str, df: pd.DataFrame) -> None:
    """Expect columns: [open,high,low,close,volume]; index = date (UTC-normalized)."""
    path = _cache_path(symbol)
    df.to_csv(path, index_label="date")

def load_from_cache(symbol: str) -> pd.DataFrame | None:
    path = _cache_path(symbol)
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    return df

# ----- Validation hooks (extend later) -----

def validate_non_empty(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        raise ValidationError(f"{symbol}: empty dataframe")

def validate_columns(df: pd.DataFrame, symbol: str):
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValidationError(f"{symbol}: missing columns {sorted(missing)}")

def validate_sorted_unique(df: pd.DataFrame, symbol: str):
    if not df.index.is_monotonic_increasing:
        raise ValidationError(f"{symbol}: index not sorted ascending")
    if df.index.duplicated().any():
        raise ValidationError(f"{symbol}: duplicate dates in index")

def validate_recent(df: pd.DataFrame, symbol: str, max_lag_days: int = 3):
    """For EOD data; allow weekends/holidays with a small lag tolerance."""
    if df.empty: return
    last = pd.to_datetime(df.index[-1]).tz_localize("UTC") if df.index.tz is None else df.index[-1]
    now = datetime.now(timezone.utc)
    lag = (now - last).days
    if lag > max_lag_days:
        raise ValidationError(f"{symbol}: data stale (last={last.date()}, lag={lag}d)")

def validate_volume(df: pd.DataFrame, symbol: str, min_vol: int = 1000):
    if df["volume"].iloc[-1] < min_vol:
        raise ValidationError(f"{symbol}: suspiciously low volume {df['volume'].iloc[-1]}")

def run_validations(df: pd.DataFrame, symbol: str):
    validate_non_empty(df, symbol)
    validate_columns(df, symbol)
    validate_sorted_unique(df, symbol)
    validate_recent(df, symbol)
    validate_volume(df, symbol)

# ----- Public interface (API-agnostic for now) -----

def get_daily_bars(symbol: str) -> pd.DataFrame:
    """
    1) Try cache
    2) (Later) Try provider(s)
    3) Validate
    """
    df = load_from_cache(symbol)
    if df is None:
        raise DataError(f"No cached data for {symbol}. Add a provider or seed the cache.")

    run_validations(df, symbol)
    return df

# Utility to seed cache with a dataframe (for tests/mock runs)
def seed_cache(symbol: str, df: pd.DataFrame) -> None:
    """Normalize index to UTC date and save."""
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize("UTC").normalize()
    save_to_cache(symbol, df)
