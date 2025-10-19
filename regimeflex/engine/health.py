# engine/health.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

from .config import Config
from .env import load_env
from .identity import RegimeFlexIdentity as RF
from .killswitch import is_killed
from .data import load_from_cache
from .data import save_to_cache  # used only to test write access if needed

@dataclass
class CheckResult:
    name: str
    status: str   # "PASS" | "WARN" | "FAIL"
    detail: str

@dataclass
class HealthReport:
    status: str               # overall: PASS if no FAIL; WARN if any WARN; else PASS
    checks: List[CheckResult]
    timestamp: str

def _ok_dir_write(path: Path) -> Tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".health_write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True, "writable"
    except Exception as e:
        return False, f"not writable: {e}"

def _bool_to_status(ok: bool, warn: bool = False) -> str:
    if ok: return "PASS"
    return "WARN" if warn else "FAIL"

def run_health() -> HealthReport:
    checks: List[CheckResult] = []
    cfg = Config(".")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1) Kill-switch
    killed = is_killed()
    checks.append(CheckResult("kill_switch", "FAIL" if killed else "PASS",
                              "enabled" if killed else "disabled"))

    # 2) Config presence (essential ones only)
    essential = [
        "config/run.yaml",
        "config/exposure.yaml",
        "config/broker.yaml",
        "config/schedule.yaml",
        "config/data.yaml",
        "config/telemetry.yaml",
        "config/logs.yaml",
    ]
    missing = [p for p in essential if not (Path(p).exists())]
    checks.append(CheckResult("configs_present",
                              _bool_to_status(len(missing) == 0),
                              "missing: " + ", ".join(missing) if missing else "all present"))

    # 3) Broker safety
    broker = cfg._load_yaml("config/broker.yaml")
    alp = (broker.get("alpaca") or {})
    dry_run = bool(alp.get("dry_run", True))
    mode = alp.get("mode", "paper")
    env = load_env()
    has_keys = bool(env.alpaca_key and env.alpaca_secret)
    if dry_run:
        checks.append(CheckResult("broker_mode", "PASS", f"dry_run=true ({mode})"))
    else:
        checks.append(CheckResult("broker_mode",
                                  _bool_to_status(has_keys, warn=False),
                                  "ready" if has_keys else "dry_run=false but missing Alpaca keys"))

    # 4) Data readiness (cache freshness present at least for QQQ/PSQ)
    data_cfg = cfg._load_yaml("config/data.yaml")
    symbols = data_cfg.get("symbols", ["QQQ", "PSQ"])
    stale: List[str] = []
    absent: List[str] = []
    for sym in symbols:
        df = load_from_cache(sym)
        if df is None or df.empty:
            absent.append(sym)
        else:
            # consider "fresh" if last bar date within 7 calendar days (EOD systems tolerate lag)
            last_date = df.index[-1].date()
            age = (datetime.now(timezone.utc).date() - last_date).days
            if age > 7:
                stale.append(f"{sym}({age}d)")
    if absent:
        checks.append(CheckResult("data_cache", "WARN", f"missing cache: {', '.join(absent)}"))
    elif stale:
        checks.append(CheckResult("data_cache", "WARN", f"stale cache: {', '.join(stale)}"))
    else:
        checks.append(CheckResult("data_cache", "PASS", "QQQ/PSQ cache OK"))

    # 5) Logs/Audit write access
    writable_dirs = ["logs/audit", "logs/trading", "reports"]
    write_issues = []
    for d in writable_dirs:
        ok, msg = _ok_dir_write(Path(d))
        if not ok: write_issues.append(f"{d}({msg})")
    checks.append(CheckResult("fs_permissions",
                              _bool_to_status(len(write_issues) == 0),
                              "OK" if not write_issues else "; ".join(write_issues)))

    # 6) Telemetry (won't fail the system if missing, only warn)
    try:
        tele = cfg.telemetry or {}
    except Exception:
        tele = {}
    if tele.get("enabled", True):
        # if enabled but no token/chat → WARN
        token_present = bool(getattr(env, "telegram_bot_token", None))
        chat_present  = bool(getattr(env, "telegram_chat_id", None))
        if token_present and chat_present:
            checks.append(CheckResult("telemetry", "PASS", "telegram configured"))
        else:
            checks.append(CheckResult("telemetry", "WARN", "enabled but token/chat missing → will DRY-RUN"))
    else:
        checks.append(CheckResult("telemetry", "PASS", "disabled"))

    # 7) EOD guard config sanity
    sched = cfg._load_yaml("config/schedule.yaml")
    guard = (sched.get("eod_guard") or {})
    try:
        win = int(guard.get("min_minutes_before_close", 30))
        checks.append(CheckResult("eod_guard", "PASS", f"window={win}m; override={bool(guard.get('allow_early_override', False))}"))
    except Exception as e:
        checks.append(CheckResult("eod_guard", "FAIL", f"invalid config: {e}"))

    # Overall status
    overall = "PASS"
    if any(c.status == "FAIL" for c in checks):
        overall = "FAIL"
    elif any(c.status == "WARN" for c in checks):
        overall = "WARN"

    RF.print_log(f"Health overall: {overall}", "RISK" if overall != "PASS" else "SUCCESS")
    return HealthReport(status=overall, checks=checks, timestamp=now)
