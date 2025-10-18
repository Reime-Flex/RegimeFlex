from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os
import requests
import pandas as pd

from .identity import RegimeFlexIdentity as RF

def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

def _iso_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

def fetch_polygon_daily(symbol: str, days: int, base_url: str, api_key: Optional[str]) -> Optional[pd.DataFrame]:
    if not api_key:
        RF.print_log("Polygon key missing — dry-run, returning None", "RISK")
        return None
    start, end = _iso_days_ago(days), _iso_today()
    url = base_url.format(symbol=symbol, _symbol=symbol, **{"from": start, "to": end})
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key}
    RF.print_log(f"Polygon GET {symbol} {start}→{end}", "INFO")
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        RF.print_log(f"Polygon API error: {e}", "RISK")
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
