# engine/env_watchdog.py
from __future__ import annotations
import os
from typing import List, Dict

def missing_env(vars_list: List[str]) -> List[str]:
    miss = []
    for v in vars_list or []:
        if not os.environ.get(v, ""):
            miss.append(v)
    return miss

def env_guard(broker_cfg: Dict) -> Dict[str, List[str]]:
    """Return dict of missing envs per subsystem."""
    out: Dict[str, List[str]] = {}
    # Broker (Alpaca)
    alp = (broker_cfg.get("alpaca") or {})
    req = alp.get("required_env") or []
    miss = missing_env(req)
    if miss:
        out["alpaca"] = miss

    # Telemetry
    tel = (broker_cfg.get("telemetry") or {})
    req_t = tel.get("required_env") or []
    miss_t = missing_env(req_t)
    if miss_t:
        out["telemetry"] = miss_t

    return out

