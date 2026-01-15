"""
Market Data Module - Real-time and intraday data via Alpaca

Uses Alpaca for:
- Real-time quotes (bid/ask/last)
- Intraday bars (1min, 5min, 15min, 1hour)
- Account and position data

Uses Polygon for:
- Historical daily bars (better history depth)
"""

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
import pandas as pd

from regimeflex.config.api_keys import APIKeys


# Alpaca API endpoints
ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_URL = "https://api.alpaca.markets"


def _get_alpaca_headers() -> Dict[str, str]:
    """Get Alpaca API headers."""
    return {
        "APCA-API-KEY-ID": APIKeys.alpaca_key_id(),
        "APCA-API-SECRET-KEY": APIKeys.alpaca_secret(),
    }


def _get_alpaca_base_url() -> str:
    """Get Alpaca trading API base URL."""
    env = os.getenv("ENV", "dev").lower()
    if env == "prod":
        return os.getenv("ALPACA_LIVE_BASE_URL", ALPACA_LIVE_URL)
    return os.getenv("ALPACA_BASE_URL", ALPACA_PAPER_URL)


def fetch_latest_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch latest quote (bid/ask/last) from Alpaca.

    Returns:
        {
            "symbol": "TQQQ",
            "last": 78.45,
            "bid": 78.44,
            "ask": 78.46,
            "bid_size": 100,
            "ask_size": 200,
            "timestamp": "2024-01-14T15:30:00Z"
        }
    """
    try:
        url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/quotes/latest"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        quote = data.get("quote", {})

        return {
            "symbol": symbol,
            "bid": quote.get("bp", 0),
            "ask": quote.get("ap", 0),
            "bid_size": quote.get("bs", 0),
            "ask_size": quote.get("as", 0),
            "timestamp": quote.get("t", ""),
        }
    except Exception as e:
        print(f"Error fetching quote for {symbol}: {e}")
        return None


def fetch_latest_trade(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch latest trade from Alpaca.

    Returns:
        {
            "symbol": "TQQQ",
            "price": 78.45,
            "size": 100,
            "timestamp": "2024-01-14T15:30:00Z"
        }
    """
    try:
        url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/trades/latest"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        trade = data.get("trade", {})

        return {
            "symbol": symbol,
            "price": trade.get("p", 0),
            "size": trade.get("s", 0),
            "timestamp": trade.get("t", ""),
        }
    except Exception as e:
        print(f"Error fetching trade for {symbol}: {e}")
        return None


def fetch_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full snapshot (quote + trade + daily bar) from Alpaca.

    Returns combined quote, trade, and daily bar data.
    """
    try:
        url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/snapshot"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()

        quote = data.get("latestQuote", {})
        trade = data.get("latestTrade", {})
        daily = data.get("dailyBar", {})
        prev_daily = data.get("prevDailyBar", {})

        last_price = trade.get("p", 0)
        prev_close = prev_daily.get("c", 0)
        change = last_price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol,
            "last": last_price,
            "bid": quote.get("bp", 0),
            "ask": quote.get("ap", 0),
            "bid_size": quote.get("bs", 0),
            "ask_size": quote.get("as", 0),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "prev_close": prev_close,
            "open": daily.get("o", 0),
            "high": daily.get("h", 0),
            "low": daily.get("l", 0),
            "volume": daily.get("v", 0),
            "timestamp": trade.get("t", ""),
        }
    except Exception as e:
        print(f"Error fetching snapshot for {symbol}: {e}")
        return None


def fetch_multi_snapshot(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetch snapshots for multiple symbols at once.

    Returns dict keyed by symbol.
    """
    try:
        symbols_param = ",".join(symbols)
        url = f"{ALPACA_DATA_URL}/v2/stocks/snapshots?symbols={symbols_param}"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return {}

        data = resp.json()
        result = {}

        for symbol, snapshot in data.items():
            quote = snapshot.get("latestQuote", {})
            trade = snapshot.get("latestTrade", {})
            daily = snapshot.get("dailyBar", {})
            prev_daily = snapshot.get("prevDailyBar", {})

            last_price = trade.get("p", 0)
            prev_close = prev_daily.get("c", 0)
            change = last_price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[symbol] = {
                "symbol": symbol,
                "last": last_price,
                "bid": quote.get("bp", 0),
                "ask": quote.get("ap", 0),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": prev_close,
                "open": daily.get("o", 0),
                "high": daily.get("h", 0),
                "low": daily.get("l", 0),
                "volume": daily.get("v", 0),
            }

        return result
    except Exception as e:
        print(f"Error fetching multi snapshot: {e}")
        return {}


def fetch_intraday_bars(
    symbol: str,
    timeframe: str = "5Min",
    limit: int = 100,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch intraday bars from Alpaca.

    Args:
        symbol: Stock symbol (e.g., "TQQQ")
        timeframe: "1Min", "5Min", "15Min", "1Hour", "1Day"
        limit: Number of bars to fetch (max 10000)
        start: Start time ISO format (optional)
        end: End time ISO format (optional)

    Returns:
        List of OHLCV bars:
        [
            {"t": "2024-01-14T15:30:00Z", "o": 78.40, "h": 78.50, "l": 78.35, "c": 78.45, "v": 1000},
            ...
        ]
    """
    try:
        url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "limit": min(limit, 10000),
            "adjustment": "all",
            "feed": "iex",  # Use IEX for free tier
        }

        if start:
            params["start"] = start
        if end:
            params["end"] = end

        resp = requests.get(url, headers=_get_alpaca_headers(), params=params, timeout=15)

        if resp.status_code != 200:
            return None

        data = resp.json()
        bars = data.get("bars") or []  # Handle null/None from API

        if not bars:
            return []

        return [
            {
                "t": bar.get("t"),
                "o": bar.get("o"),
                "h": bar.get("h"),
                "l": bar.get("l"),
                "c": bar.get("c"),
                "v": bar.get("v"),
            }
            for bar in bars
        ]
    except Exception as e:
        print(f"Error fetching intraday bars for {symbol}: {e}")
        return None


def fetch_account() -> Optional[Dict[str, Any]]:
    """
    Fetch Alpaca account information.

    Returns:
        {
            "equity": 100000.00,
            "cash": 50000.00,
            "buying_power": 200000.00,
            "portfolio_value": 100000.00,
            "last_equity": 99500.00,
            "day_pnl": 500.00,
            "day_pnl_pct": 0.50,
        }
    """
    try:
        url = f"{_get_alpaca_base_url()}/v2/account"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()

        equity = float(data.get("equity", 0))
        last_equity = float(data.get("last_equity", 0))
        day_pnl = equity - last_equity
        day_pnl_pct = (day_pnl / last_equity * 100) if last_equity else 0

        return {
            "equity": equity,
            "cash": float(data.get("cash", 0)),
            "buying_power": float(data.get("buying_power", 0)),
            "portfolio_value": float(data.get("portfolio_value", 0)),
            "last_equity": last_equity,
            "day_pnl": round(day_pnl, 2),
            "day_pnl_pct": round(day_pnl_pct, 2),
            "pattern_day_trader": data.get("pattern_day_trader", False),
            "trading_blocked": data.get("trading_blocked", False),
            "account_blocked": data.get("account_blocked", False),
        }
    except Exception as e:
        print(f"Error fetching account: {e}")
        return None


def fetch_positions() -> List[Dict[str, Any]]:
    """
    Fetch current positions from Alpaca.

    Returns:
        [
            {
                "symbol": "TQQQ",
                "qty": 100,
                "side": "long",
                "avg_entry": 78.00,
                "current_price": 78.45,
                "market_value": 7845.00,
                "unrealized_pnl": 45.00,
                "unrealized_pnl_pct": 0.58,
            },
            ...
        ]
    """
    try:
        url = f"{_get_alpaca_base_url()}/v2/positions"
        resp = requests.get(url, headers=_get_alpaca_headers(), timeout=10)

        if resp.status_code != 200:
            return []

        data = resp.json()

        positions = []
        for pos in data:
            qty = float(pos.get("qty", 0))
            positions.append({
                "symbol": pos.get("symbol"),
                "qty": abs(qty),
                "side": "long" if qty > 0 else "short",
                "avg_entry": float(pos.get("avg_entry_price", 0)),
                "current_price": float(pos.get("current_price", 0)),
                "market_value": float(pos.get("market_value", 0)),
                "unrealized_pnl": float(pos.get("unrealized_pl", 0)),
                "unrealized_pnl_pct": float(pos.get("unrealized_plpc", 0)) * 100,
                "cost_basis": float(pos.get("cost_basis", 0)),
            })

        return positions
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []


def bars_to_dataframe(bars: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert bars list to pandas DataFrame."""
    if not bars:
        return pd.DataFrame()

    df = pd.DataFrame(bars)
    df["t"] = pd.to_datetime(df["t"])
    df = df.set_index("t")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df
