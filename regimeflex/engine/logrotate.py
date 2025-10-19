# engine/logrotate.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, shutil

from .identity import RegimeFlexIdentity as RF
from .config import Config

def _is_today(p: Path) -> bool:
    try:
        # expect names like ledger_YYYYMMDD.jsonl or timestamps in mtime
        stem = p.stem  # e.g., ledger_20251019
        ymd = None
        for token in stem.split("_"):
            if len(token) == 8 and token.isdigit():
                ymd = token
        if ymd:
            fdate = datetime.strptime(ymd, "%Y%m%d").date()
            return fdate == datetime.now(timezone.utc).date()
    except Exception:
        pass
    # fallback to mtime
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).date() == datetime.now(timezone.utc).date()

def _gzip_file(p: Path) -> Path:
    gz = p.with_suffix(p.suffix + ".gz")
    with p.open("rb") as fin, gzip.open(gz, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    p.unlink()  # remove original after compress
    return gz

def rotate_once(dirpath: Path, patterns: list[str], retention_days: int) -> dict:
    dirpath.mkdir(parents=True, exist_ok=True)
    archived, removed = 0, 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    # compress non-today files matching patterns
    for pat in patterns:
        for p in dirpath.glob(pat):
            if p.suffix.endswith(".gz"):
                # enforce retention on gz archives
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    p.unlink()
                    removed += 1
                continue
            # skip today's active files
            if _is_today(p):
                continue
            try:
                _gzip_file(p)
                archived += 1
            except Exception as e:
                RF.print_log(f"Rotate failed on {p}: {e}", "ERROR")

    # second pass: delete old .gz beyond retention
    for p in dirpath.glob("*.gz"):
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            p.unlink()
            removed += 1

    return {"archived": archived, "removed": removed}

def rotate_all() -> dict:
    cfg = Config(".")._load_yaml("config/logs.yaml") if (Config(".").root / "config/logs.yaml").exists() else {}
    paths = [Path(p) for p in (cfg.get("paths") or [])]
    patterns = list(cfg.get("patterns") or ["*.jsonl", "*.log"])
    retention = int(cfg.get("retention_days", 30))

    summary = {"archived": 0, "removed": 0, "dirs": 0}
    for d in paths:
        res = rotate_once(d, patterns, retention)
        summary["archived"] += res["archived"]
        summary["removed"] += res["removed"]
        summary["dirs"] += 1
    RF.print_log(f"Logrotate → dirs={summary['dirs']} archived={summary['archived']} removed={summary['removed']}", "INFO")
    return summary
