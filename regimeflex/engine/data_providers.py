from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os
import requests
import pandas as pd

from regimeflex.engine.identity import RegimeFlexIdentity as RF

def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

def _iso_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

import time
from requests.exceptions import Timeout, ConnectionError, HTTPError

class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")

class RateLimitError(APIError):
    pass

class AuthError(APIError):
    pass


def _fetch_with_retry(
    url: str,
    params: dict = None,
    headers: dict = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: int = 30
) -> Optional[dict]:
    """
    Fetch with intelligent retry logic based on error type.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Handle specific HTTP errors
            if r.status_code == 429:
                # Rate limit - exponential backoff
                delay = base_delay * (2 ** attempt)
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except: pass
                RF.print_log(f"Rate limit hit (429), waiting {delay:.1f}s before retry {attempt+1}/{max_retries}", "RISK")
                time.sleep(delay)
                continue
            
            elif r.status_code in (500, 502, 503, 504):
                # Server error - retry with delay
                delay = base_delay * (2 ** attempt)
                RF.print_log(f"Server error ({r.status_code}), waiting {delay:.1f}s before retry {attempt+1}/{max_retries}", "RISK")
                time.sleep(delay)
                continue
            
            elif r.status_code in (401, 403):
                # Auth error - don't retry, fail immediately
                raise AuthError(r.status_code, "Authentication failed - check API keys")
            
            r.raise_for_status()
            return r.json()
            
        except Timeout as e:
            RF.print_log(f"Request timeout, retry {attempt+1}/{max_retries}", "RISK")
            last_error = e
            time.sleep(base_delay)
            continue
            
        except ConnectionError as e:
            RF.print_log(f"Connection error, retry {attempt+1}/{max_retries}: {e}", "RISK")
            last_error = e
            time.sleep(base_delay * 2)
            continue
            
        except AuthError:
            raise  # Don't retry auth errors
            
        except Exception as e:
            RF.print_log(f"Unexpected error: {type(e).__name__}: {e}", "ERROR")
            last_error = e
            break
    
    RF.print_log(f"All {max_retries} retries exhausted. Last error: {last_error}", "ERROR")
    return None

def fetch_polygon_daily(symbol: str, days: int, base_url: str, api_key: Optional[str]) -> Optional[pd.DataFrame]:
    if not api_key:
        RF.print_log("Polygon key missing — dry-run, returning None", "RISK")
        return None
    
    # Use circuit breaker for Polygon API calls
    try:
        from regimeflex.engine.guardian.circuit_breaker import get_polygon_breaker, CircuitBreakerError
        breaker = get_polygon_breaker()
    except ImportError:
        class MockBreaker:
            def execute(self, f): return f()
        breaker = MockBreaker()
        CircuitBreakerError = Exception
    
    start, end = _iso_days_ago(days), _iso_today()
    url = base_url.format(symbol=symbol, _symbol=symbol, **{"from": start, "to": end})
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key}
    RF.print_log(f"Polygon GET {symbol} {start}→{end}", "INFO")
    
    try:
        # Execute via circuit breaker
        def _do_fetch():
            return _fetch_with_retry(url, params=params)
        
        try:
            j = breaker.execute(_do_fetch)
        except CircuitBreakerError as e:
            RF.print_log(f"Polygon circuit breaker open: {e}", "RISK")
            return None
        
        if j is None:
            return None
    except AuthError as e:
        RF.print_log(f"Polygon auth failed: {e}", "ERROR")
        return None

    # Expect { results: [ { t: ms, o,h,l,c,v }, ... ] }
    res = j.get("results", [])
    if not res:
        RF.print_log(f"Polygon: no results for {symbol}", "RISK")
        return None
    df = pd.DataFrame(res)
    df["date"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.normalize()
    out = pd.DataFrame({
        "open": df["o"].astype(float),
        "high": df["h"].astype(float),
        "low": df["l"].astype(float),
        "close": df["c"].astype(float),
        "volume": df["v"].astype(int)
    }, index=df["date"]).sort_index()
    return out

def fetch_alpaca_daily(symbol: str, days: int, base_url: str, key: Optional[str], secret: Optional[str]) -> Optional[pd.DataFrame]:
    if not (key and secret):
        RF.print_log("Alpaca creds missing — dry-run, returning None", "RISK")
        return None
    start, end = _iso_days_ago(days), _iso_today()
    url = base_url.format(symbol=symbol, **{"from": start, "to": end})
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    RF.print_log(f"Alpaca GET {symbol} {start}→{end}", "INFO")
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        RF.print_log(f"Alpaca API error: {e}", "RISK")
        return None
    bars = (j.get("bars") or j.get("results") or [])
    if not bars:
        RF.print_log(f"Alpaca: no results for {symbol}", "RISK")
        return None
    df = pd.DataFrame(bars)
    # Alpaca v2 returns t (ISO) or "S" epoch; normalize robustly
    tcol = "t" if "t" in df.columns else "timestamp"
    ts = pd.to_datetime(df[tcol], utc=True)
    df["date"] = ts.dt.normalize()
    # Field names can be o/h/l/c/v or open/high/low/close/volume
    def col(*cands): 
        for c in cands:
            if c in df.columns: return c
        return None
    out = pd.DataFrame({
        "open":  df[col("o","open")].astype(float),
        "high":  df[col("h","high")].astype(float),
        "low":   df[col("l","low")].astype(float),
        "close": df[col("c","close")].astype(float),
        "volume":df[col("v","volume")].astype(int),
    }, index=df["date"]).sort_index()
    return out
