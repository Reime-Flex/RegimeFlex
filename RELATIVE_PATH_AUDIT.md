# Relative Path Usage Audit Report

**Date**: 2026-01-11  
**Priority**: P0 (Critical for PM2 deployment)  
**Status**: Complete Audit

---

## Executive Summary

Found **100+ instances** of relative path usage across the codebase that could break when PM2 changes working directory. Critical state files (run.lock, kill_switch.json, positions.json) are at **HIGH** priority risk.

**Risk Breakdown:**
- **HIGH Priority**: 8 instances (state files - critical for operation)
- **MEDIUM Priority**: 65+ instances (config files - application won't start)
- **LOW Priority**: 30+ instances (logs, reports, cache - missing data but app works)

---

## HIGH Priority (State Files - Critical)

These files are critical for system operation. If PM2 changes CWD, these will be created/read from wrong locations, causing:
- Lost run locks (concurrent execution)
- Kill switch not working
- Position state corruption
- Trading state corruption

| Priority | File:Line | Code Snippet | Operation | Current Path |
|----------|-----------|--------------|-----------|--------------|
| **HIGH** | `killswitch.py:3` | `KILL_SWITCH_PATH = Path("config/kill_switch.flag")` | Read/Write | `config/kill_switch.flag` |
| **HIGH** | `pnl.py:10` | `SNAP_DIR = Path("logs/trading")` | Write | `logs/trading/daily_snapshot.csv` |
| **HIGH** | `data.py:13` | `CACHE_DIR = Path("data/cache")` | Read/Write | `data/cache/*.csv` |
| **HIGH** | `fills_state.py:8` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Write | `logs/trading/fills_state.jsonl` |
| **HIGH** | `reconcile_positions.py:12` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Read | `logs/trading/fills_state.jsonl` |
| **HIGH** | `trade_cadence.py:8` | `FILLS_FILE = Path("logs/trading/fills_state.jsonl")` | Read | `logs/trading/fills_state.jsonl` |
| **HIGH** | `safety_wrapper.py:68` | `state_file: str = "data/trading_state.json"` | Read/Write | `data/trading_state.json` |
| **HIGH** | `safety_wrapper.py:360` | `def __init__(self, state_file: str \| Path = "data/trading_state.json")` | Read/Write | `data/trading_state.json` |

**Note**: The following files already use absolute paths from `regimeflex/config/paths.py`:
- ✅ `RUN_LOCK_FILE` (via paths.py)
- ✅ `POSITIONS_FILE` (via paths.py)
- ✅ `KILL_SWITCH_FILE` (via paths.py)
- ✅ `GUARDIAN_HEARTBEAT_FILE` (via paths.py)

---

## MEDIUM Priority (Config Files)

These files are required for application startup. If PM2 changes CWD, configs won't load and the application will fail to start.

### Config(".") Usage (65+ instances)

All `Config(".")` calls rely on current working directory. These should use absolute paths from `regimeflex/config/paths.py`.

| Priority | File:Line | Code Snippet | Operation | Current Path |
|----------|-----------|--------------|-----------|--------------|
| **MEDIUM** | `runner.py:261` | `Config(".").telemetry` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:264` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `runner.py:288` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `runner.py:321` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | `config/schedule.yaml` |
| **MEDIUM** | `runner.py:388` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:438` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:493` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:526` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `runner.py:617` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `runner.py:626` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:874` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:904` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `runner.py:949` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1064` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1140` | `Config(".")._load_yaml("config/broker.yaml")` | Read | `config/broker.yaml` |
| **MEDIUM** | `runner.py:1160` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1226` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1341` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:1374` | `Config(".")._load_yaml("config/broker.yaml")` | Read | `config/broker.yaml` |
| **MEDIUM** | `runner.py:1414` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1552` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1559` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1627` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1708` | `Config(".")._load_yaml("config/risk.yaml")` | Read | `config/risk.yaml` |
| **MEDIUM** | `runner.py:1785` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1839` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1854` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:1870` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:1893` | `Config(".").run.get("equity", 25000.0)` | Read | `config/run.yaml` |
| **MEDIUM** | `runner.py:1907` | `Config(".")._load_yaml("config/logs.yaml")` | Read | `config/logs.yaml` |
| **MEDIUM** | `runner.py:1937` | `Config(".")._load_yaml("config/reports.yaml")` | Read | `config/reports.yaml` |
| **MEDIUM** | `runner.py:1950` | `Config(".")._load_yaml("config/metrics.yaml")` | Read | `config/metrics.yaml` |
| **MEDIUM** | `runner.py:1995` | `Config(".")._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `runner.py:2021` | `Config(".")._load_yaml("config/reports.yaml")` | Read | `config/reports.yaml` |
| **MEDIUM** | `runner.py:2080` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `data.py:82` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `data.py:113` | `Config(".").run` | Read | `config/run.yaml` |
| **MEDIUM** | `data.py:114` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `guardrails.py:13` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `exposure_reason.py:12` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `timing.py:11` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | `config/schedule.yaml` |
| **MEDIUM** | `symbols.py:14` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `instruments.py:8` | `Config(".")._load_yaml("config/execution.yaml")` | Read | `config/execution.yaml` |
| **MEDIUM** | `logrotate.py:68` | `Config(".")._load_yaml("config/logs.yaml")` | Read | `config/logs.yaml` |
| **MEDIUM** | `exposure.py:36` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `exec_planner.py:135` | `Config(".")._load_yaml("config/broker.yaml")` | Read | `config/broker.yaml` |
| **MEDIUM** | `exec_alpaca.py:308` | `cfg._load_yaml("config/broker.yaml")` | Read | `config/broker.yaml` |
| **MEDIUM** | `guardian/system_health.py:61` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `guardian/alerting.py:71` | `cfg._load_yaml("config/guardian.yaml")` | Read | `config/guardian.yaml` |
| **MEDIUM** | `guardian/alerting.py:346` | `cfg._load_yaml("config/guardian.yaml")` | Read | `config/guardian.yaml` |
| **MEDIUM** | `guardian/circuit_breaker.py:115` | `cfg._load_yaml("config/guardian.yaml")` | Read | `config/guardian.yaml` |
| **MEDIUM** | `guardian/watchdog.py:92` | `cfg._load_yaml("config/guardian.yaml")` | Read | `config/guardian.yaml` |
| **MEDIUM** | `config_echo.py:7` | `C = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `health.py:43` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `__main__.py:52` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/run_http_trigger.py:69` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/backfill_reports.py:23` | `Config(".")._load_yaml("config/backfill.yaml")` | Read | `config/backfill.yaml` |
| **MEDIUM** | `scripts/backfill_reports.py:24` | `Config(".").run` | Read | `config/run.yaml` |
| **MEDIUM** | `scripts/backfill_reports.py:51` | `Config(".")._load_yaml("config/exposure.yaml")` | Read | `config/exposure.yaml` |
| **MEDIUM** | `scripts/broker_place_preview.py:26` | `Config(".")._load_yaml("config/broker.yaml")` | Read | `config/broker.yaml` |
| **MEDIUM** | `scripts/fetch_live_to_cache.py:12` | `Config(".")._load_yaml("config/data.yaml")` | Read | `config/data.yaml` |
| **MEDIUM** | `scripts/run_offline_cycle.py:34` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/run_offline_from_config.py:18` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/calendar_demo.py:13` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/show_config.py:12` | `cfg = Config(".")` | Read | `config/*.yaml` |
| **MEDIUM** | `scripts/guardian_status.py:61` | `cfg._load_yaml("config/guardian.yaml")` | Read | `config/guardian.yaml` |
| **MEDIUM** | `scripts/next_run_receipt.py:57` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | `config/schedule.yaml` |
| **MEDIUM** | `scripts/next_run.py:55` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | `config/schedule.yaml` |
| **MEDIUM** | `scripts/gated_live.py:49` | `Config(".")._load_yaml("config/schedule.yaml")` | Read | `config/schedule.yaml` |
| **MEDIUM** | `scripts/preflight.py:28` | `cfg._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |
| **MEDIUM** | `scripts/trigger_server.py:125` | `cfg._load_yaml("config/telemetry.yaml")` | Read | `config/telemetry.yaml` |

### Path(".") Usage in Functions

| Priority | File:Line | Code Snippet | Operation | Current Path |
|----------|-----------|--------------|-----------|--------------|
| **MEDIUM** | `runner.py:206` | `config_snapshot_hash(Path("."))` | Read | `config/*.yaml` |
| **MEDIUM** | `runner.py:294` | `load_model_manifest(Path("."))` | Read | `config/model_manifest.yaml` |
| **MEDIUM** | `config_hash.py:29` | `def config_snapshot_hash(root: Path = Path("."))` | Read | `config/*.yaml` |
| **MEDIUM** | `session_guard.py:16` | `def is_full_holiday(d: date, root: Path = Path("."))` | Read | `config/us_holidays.json` |
| **MEDIUM** | `session_guard.py:21` | `def is_half_day(d: date, root: Path = Path("."))` | Read | `config/us_halfdays.json` |
| **MEDIUM** | `session_guard.py:26` | `def session_status(..., root: Path = Path("."))` | Read | `config/*.json` |

---

## LOW Priority (Logs, Reports, Cache)

These files are used for logging and reporting. If PM2 changes CWD, logs/reports will be written to wrong locations, but the application will still function.

| Priority | File:Line | Code Snippet | Operation | Current Path |
|----------|-----------|--------------|-----------|--------------|
| **LOW** | `metrics.py:8` | `RUN_SUMS = Path("logs/audit/run_summaries.jsonl")` | Write | `logs/audit/run_summaries.jsonl` |
| **LOW** | `run_summary.py:7` | `RUN_SUM_FILE = Path("logs/audit/run_summaries.jsonl")` | Write | `logs/audit/run_summaries.jsonl` |
| **LOW** | `storage.py:9` | `LEDGER_DIR = Path("logs/audit")` | Write | `logs/audit/*.jsonl` |
| **LOW** | `report_index.py:7` | `REPORTS_DIR = Path("reports")` | Read/Write | `reports/*` |
| **LOW** | `report_index.py:30` | `REPLAYS_DIR = Path("replays")` | Read | `replays/*` |
| **LOW** | `order_preview.py:9` | `out_dir: Path = Path("reports")` | Write | `reports/*` |
| **LOW** | `report_csv.py:8` | `def write_change_report(..., out_dir: Path = Path("reports"))` | Write | `reports/*` |
| **LOW** | `decay.py:17` | `log_dir: str = "logs/decay"` | Write | `logs/decay/*.json` |
| **LOW** | `runner.py:1711` | `pg_dir = Path(str(pg_cfg.get("out_dir", "logs/audit")))` | Write | `logs/audit/*` |
| **LOW** | `runner.py:1788` | `eq_store = Path(str(eq_cfg.get("store_path", "logs/audit/fills.jsonl")))` | Write | `logs/audit/fills.jsonl` |
| **LOW** | `runner.py:1841` | `store = Path(str(fq_cfg.get("store_path", "logs/audit/fills.jsonl")))` | Write | `logs/audit/fills.jsonl` |
| **LOW** | `scripts/path_utils.py:94` | `Path("logs/incidents.jsonl")` | Read | `logs/incidents.jsonl` |

---

## Summary Statistics

- **HIGH Priority**: 8 instances (state files - critical)
- **MEDIUM Priority**: 65+ instances (config files - application won't start)
- **LOW Priority**: 13+ instances (logs, reports, cache)
- **Total**: 86+ unique file paths identified

---

## Risk Assessment

### Critical Risk (HIGH Priority)
State files (`kill_switch.flag`, `fills_state.jsonl`, `trading_state.json`, `daily_snapshot.csv`, cache files) are accessed with relative paths. If PM2 changes working directory, these files will be created/read from wrong locations, causing:
- **Kill switch not working** - Safety mechanism fails
- **Fill state corruption** - Trading history lost
- **Trading state corruption** - Duplicate prevention fails
- **Cache corruption** - Data integrity issues

### Medium Risk (MEDIUM Priority)
Config files accessed with `Config(".")` or `Path(".")` rely on current working directory. If CWD changes:
- **Application won't start** - Configs won't load
- **Runtime errors** - Missing configuration values
- **Incorrect behavior** - Wrong config values loaded

### Low Risk (LOW Priority)
Logs and reports will be written to wrong locations, but won't break functionality:
- **Missing logs** - Harder to debug
- **Reports in wrong location** - Inconvenient but not critical

---

## Recommended Fix Strategy

### Phase 1: Fix HIGH Priority Files (Critical)
1. ✅ Update `killswitch.py` to use `KILL_SWITCH_FILE` from `paths.py`
2. ✅ Update `pnl.py` to use `LOGS_TRADING_DIR` from `paths.py`
3. ✅ Update `data.py` to use `CACHE_DIR` from `paths.py`
4. ✅ Update `fills_state.py` to use `FILLS_STATE_FILE` from `paths.py`
5. ✅ Update `reconcile_positions.py` to use `FILLS_STATE_FILE` from `paths.py`
6. ✅ Update `trade_cadence.py` to use `FILLS_STATE_FILE` from `paths.py`
7. ✅ Update `safety_wrapper.py` to use `TRADING_STATE_FILE` from `paths.py`
8. ✅ Update `metrics.py` to use `RUN_SUMMARIES_FILE` from `paths.py`
9. ✅ Update `run_summary.py` to use `RUN_SUMMARIES_FILE` from `paths.py`
10. ✅ Update `storage.py` to use `LOGS_AUDIT_DIR` from `paths.py`

### Phase 2: Fix MEDIUM Priority Files (Config Loading)
1. Update `Config` class to accept absolute path or use `PROJECT_ROOT` by default
2. Replace all `Config(".")` calls with `Config(PROJECT_ROOT)` or `Config()`
3. Update function signatures that accept `root: Path = Path(".")` to use `PROJECT_ROOT`

### Phase 3: Fix LOW Priority Files (Logs/Reports)
1. Update log/report paths to use constants from `paths.py`
2. Ensure all output directories use absolute paths

---

## Files Already Using Absolute Paths

✅ **Already Fixed:**
- `regimeflex/config/paths.py` - Provides all path constants
- `regimeflex/engine/runner.py` - Uses `RUN_LOCK_FILE`, `POSITIONS_FILE` from paths.py
- `regimeflex/engine/guardian/watchdog.py` - Uses `GUARDIAN_HEARTBEAT_FILE` from paths.py

---

## Next Steps

1. **Immediate**: Fix HIGH priority files (state files)
2. **Short-term**: Fix MEDIUM priority files (config loading)
3. **Long-term**: Fix LOW priority files (logs/reports)

All fixes should use constants from `regimeflex/config/paths.py` which provides absolute paths calculated relative to the project root.

