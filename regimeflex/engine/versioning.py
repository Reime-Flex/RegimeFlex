# engine/versioning.py
from __future__ import annotations
import sys, platform

def safe_version(mod_name: str) -> str:
    try:
        m = __import__(mod_name)
        v = getattr(m, "__version__", None)
        return str(v) if v else "unknown"
    except Exception:
        return "missing"

def runtime_versions() -> dict:
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "pandas": safe_version("pandas"),
        "numpy": safe_version("numpy"),
        "alpaca_trade_api": safe_version("alpaca_trade_api"),
        "python_telegram_bot": safe_version("telegram"),
    }
