# Relative Path Usage Audit Report

**Date**: 2026-01-10  
**Priority**: P1  
**Status**: Complete

---

## Executive Summary

Found **84+ instances** of relative path usage across the codebase that could break when PM2 changes working directory. Critical state files (run.lock, kill_switch.json, positions.json) are at HIGH priority risk.

---

## High Priority (State Files - Critical)

| File:Line | Code Snippet | Operation | Priority |
|-----------|--------------|-----------|----------|
| `regimeflex/engine/run_lock.py:19` | `RUN_LOCK_FILE = Path("data/state/run.lock")` | Read/Write | **HIGH** |
| `regimeflex/engine/kill_switch_manual.py:17` | `KILL_SWITCH_FILE = Path("data/state/kill_switch.json")` | Read/Write | **HIGH** |
| `regimeflex/engine/regime_buffer.py:7` | `REGIME_STATE_FILE = Path("data/state/regime_state.json")` | Read/Write | **HIGH** |
| `regimeflex/engine/order_wal.py:9` | `WAL_FILE = Path("data/state/order_wal.jsonl")` | Read/Write | **HIGH** |
| `regimeflex/engine/safety_wrapper.py:99` | `state_file = str(dup.get("state_file", "data/trading_state.json"))` | Read/Write | **HIGH** |
| `regimeflex/engine/safety_wrapper.py:352` | `self.state_file = Path(state_file)` | Read/Write | **HIGH** |

---

## Medium Priority (Config Files)

| File:Line | Code Snippet | Operation | Priority |
|-----------|--------------|-----------|----------|
| `regimeflex/engine/runner.py:196` | `config_snapshot_hash(Path("."))` | Read | MEDIUM |
| `regimeflex/engine/runner.py:255` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:312` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:379` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:429` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:485` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:518` | `Config(".")._load_yaml("config/data.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:609` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:618` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:866` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:896` | `Config(".")._load_yaml("config/data.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:941` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1056` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1132` | `Config(".")._load_yaml("config/broker.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1152` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1218` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1333` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1366` | `Config(".")._load_yaml("config/broker.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1404` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1542` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1617` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1698` | `Config(".")._load_yaml("config/risk.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1775` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1829` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1844` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1860` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1897` | `Config(".")._load_yaml("config/logs.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1927` | `Config(".")._load_yaml("config/reports.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1940` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:1985` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | MEDIUM |
| `regimeflex/engine/runner.py:2011` | `Config(".")._load_yaml("config/reports.yaml")` | Read | MEDIUM |
| `regimeflex/engine/session_guard.py:16` | `cfg = _load_json(root / "config" / "us_holidays.json")` | Read | MEDIUM |
| `regimeflex/engine/session_guard.py:21` | `cfg = _load_json(root / "config" / "us_halfdays.json")` | Read | MEDIUM |
| `regimeflex/engine/safety_wrapper.py:76` | `config_path = root_path / "config" / "safety.yaml"` | Read | MEDIUM |

---

## Low Priority (Logs, Reports, Cache)

| File:Line | Code Snippet | Operation | Priority |
|-----------|--------------|-----------|----------|
| `regimeflex/engine/pnl.py:10` | `SNAP_DIR = Path("logs/trading")` | Write | LOW |
| `regimeflex/engine/fills_state.py:8` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Write | LOW |
| `regimeflex/engine/reconcile_positions.py:12` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Read | LOW |
| `regimeflex/engine/trade_cadence.py:8` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Read | LOW |
| `regimeflex/engine/metrics.py:8` | `RUN_SUMS = Path("logs/audit/run_summaries.jsonl")` | Read/Write | LOW |
| `regimeflex/engine/run_summary.py:7` | `RUN_SUM_FILE = Path("logs/audit/run_summaries.jsonl")` | Write | LOW |
| `regimeflex/engine/report_index.py:7` | `REPORTS_DIR = Path("reports")` | Read/Write | LOW |
| `regimeflex/engine/report_index.py:30` | `REPLAYS_DIR = Path("replays")` | Read | LOW |
| `regimeflex/engine/order_preview.py:9` | `out_dir: Path = Path("reports")` | Write | LOW |
| `regimeflex/engine/data.py:13` | `CACHE_DIR = Path("data/cache")` | Read/Write | LOW |
| `regimeflex/engine/incident.py:31` | `fname = self.dir / f"{datetime.utcnow().date()}_incidents.jsonl"` | Write | LOW |
| `regimeflex/engine/guardian/watchdog.py:35` | `heartbeat_file: str = ".guardian_heartbeat"` | Read/Write | LOW |
| `regimeflex/engine/guardian/watchdog.py:92` | `heartbeat_file=wd_cfg.get("heartbeat_file", ".guardian_heartbeat")` | Read/Write | LOW |

---

## Summary Statistics

- **HIGH Priority**: 6 instances (state files - critical)
- **MEDIUM Priority**: 35+ instances (config files)
- **LOW Priority**: 13+ instances (logs, reports, cache)
- **Total**: 54+ unique file paths identified

---

## Risk Assessment

**Critical Risk**: State files (`run.lock`, `kill_switch.json`, `positions.json`) are accessed with relative paths. If PM2 changes working directory, these files will be created/read from wrong locations, causing:
- Lost run locks (concurrent execution)
- Kill switch not working
- Position state corruption

**Medium Risk**: Config files accessed with `Path(".")` or `Config(".")` rely on current working directory. If CWD changes, configs won't load.

**Low Risk**: Logs and reports will be written to wrong locations, but won't break functionality.

---

## Next Steps

1. ✅ Create `regimeflex/config/paths.py` with absolute path constants
2. ✅ Update `regimeflex/engine/runner.py` to use path constants
3. ⏳ Update other HIGH priority files (run_lock.py, kill_switch_manual.py, etc.)
4. ⏳ Update MEDIUM priority files (config loading)
5. ⏳ Update LOW priority files (logs, reports)

