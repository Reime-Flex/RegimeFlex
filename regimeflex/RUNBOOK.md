# RegimeFlex Operator Runbook

**Purpose:** One page to run, pause, update, and audit the EOD TQQQ/SQQQ system.

---

## 0) Quick Facts
- **Mode:** 100% systematic, EOD, one decision ~10 min before close.
- **Default Safety:** Paper Alpaca + dry-run true. Kill-switch supported.
- **Core entrypoint:** `python scripts/run_offline_from_config.py`
- **HTTP trigger (cron):** `GET /trigger-daily` (Flask)
- **Primary config files:** under `config/` (see §8)

---

## 1) Daily Flow (manual)
```bash
# Option A: cache/lab run (offline)
python scripts/run_offline_from_config.py

# Option B: quick backtest smoke
python scripts/backtest_preview.py
```

**Outputs**

* HTML report: `reports/daily_report_*.html`
* Audit ledger: `logs/audit/ledger_YYYYMMDD.jsonl`
* Snapshot CSV: `logs/trading/daily_snapshot.csv`
* Telegram (if enabled): summary with config hash

---

## 2) Kill-Switch (absolute stop)

```bash
# Toggle
python scripts/kill_switch.py

# Status
test -f config/kill_switch.flag && echo "ENABLED" || echo "DISABLED"
```

**When enabled:** `/trigger-daily` returns HTTP 423 and the runner exits before plan/broker/sim-fills.

---

## 3) EOD Timing Guard

* Controlled by `config/schedule.yaml`:

```yaml
eod_guard:
  min_minutes_before_close: 30
  allow_early_override: false
```

* If `minutes_to_close` > window and no override → run exits early (safe).

---

## 4) Broker Modes (paper vs live, dry-run)

`config/broker.yaml`:

```yaml
alpaca:
  mode: "paper"     # "paper" | "live"
  dry_run: true     # true = do not POST orders
constraints:
  lot_size: 1
  min_qty: 1
  qty_precision: 0
  min_notional: 200.0
```

**Paper-first checklist**

1. Keep `dry_run: true` for dress rehearsals (payloads only).
2. Flip `dry_run: false` for real **paper** orders.
3. Only after paper burn-in, change `mode: "live"` (optional).

---

## 5) Sizing/Exposure Controls

* Allocator & limits: `config/exposure.yaml`

```yaml
trend: { fast_ma: 20, slow_ma: 250 }
weights:
  base_risk: 1.0
  max_exposure_pct: 1.0
  min_exposure_pct: 0.0
  extension_factor: 2.5
  bb_period: 20
  bb_std: 2.0
confirmation:
  momentum_requires_close_above_fast: true
  momentum_requires_slope_up: true
vol_dampener:
  enabled: true
  lookback_days: 20
  cap_rvol: 0.25
  floor_scale: 0.60
limits:
  max_gross: 1.00
  max_tqqq: 1.00
  max_sqqq: 1.00
```

* Guardrails and sizing are logged; violations are clamped and noted.

---

## 6) Data Sources / Refresh

* Provider switch: `config/data.yaml`

```yaml
provider: "cache"  # cache | polygon | alpaca
symbols: ["QQQ","PSQ"]
lookback_days: 800
force_refresh: false
```

* Seed/refresh cache:

```bash
python scripts/fetch_live_to_cache.py
```

(If keys missing → dry-run logs and fallback to cache.)

---

## 7) HTTP Trigger (for cron)

* Local: `python scripts/run_http_trigger.py` then `GET http://127.0.0.1:5000/trigger-daily`
* Deployed (Railway/Vercel): `https://<app>.railway.app/trigger-daily`
* Kill-switch returns 423 with `{ "status": "killed" }`.

---

## 8) Config Fingerprint & Audit

* Every run records a config hash and writes `CFG` entry to the ledger.
* Find today's ledger:

```
logs/audit/ledger_YYYYMMDD.jsonl
```

* Entry kinds: `CFG`, `PLAN`, `ORDER`, `FILL`
* Short hash appears in HTML report "Breadcrumbs".

---

## 9) Log Rotation

* Config: `config/logs.yaml`

```yaml
rotate_on_run: true
retention_days: 30
paths: ["logs/audit","logs/trading","logs/signals"]
patterns: ["*.jsonl","*.log"]
```

* Manual rotation: `python scripts/rotate_logs.py`

---

## 10) Telemetry

* `config/telemetry.yaml`

```yaml
enabled: true
channel: "telegram"
verbosity: "brief"   # or "full"
```

* If tokens absent, messages print as "[TELEGRAM DRY-RUN]".

---

## 11) End-to-End Paper Placement (safe)

```bash
# ensure .env has ALPACA_KEY and ALPACA_SECRET
# set broker.yaml → mode: "paper", dry_run: false
python scripts/broker_place_preview.py
```

Expected: `[LIVE] POST ...` then `Accepted order id=...`. ORDER response logged to audit.

---

## 12) Cron Scheduling (cron-job.org)

* URL: `https://<app>.railway.app/trigger-daily`
* Schedule (Mon–Fri @ 20:00 UTC): `0 20 * * 1-5`
* Notify on error/timeout.
* Validate kill-switch behavior: enable switch → expect 423.

---

## 13) Incident Response

**Symptom:** Unexpected trades or sizes

* Check ledger for `CFG` hash and `PLAN/ORDER` reasons.
* Confirm `constraints` and `limits` were applied (log mentions).
* Kill-switch immediately if needed, then investigate.

**Symptom:** Data gaps

* Run `scripts/fetch_live_to_cache.py`; inspect cache CSVs and validation logs.

**Symptom:** Broker rejects order

* See `ORDER` entry in ledger for response payload.
* Verify `constraints` (lot size, min_notional) and `qty_precision`.

---

## 14) Change Control Checklist (any material change)

1. Commit config edits.
2. Run offline cycle (dry) and review HTML + ledger.
3. Run broker dry-run and check payloads.
4. Flip paper `dry_run: false` and verify accepted IDs.
5. (Optional) move to live only after paper burn-in.

---

## 15) Useful Commands (copy/paste)

```bash
# Daily run (offline + report + telemetry)
python scripts/run_offline_from_config.py

# Toggle kill-switch
python scripts/kill_switch.py

# Fetch live data to cache
python scripts/fetch_live_to_cache.py

# Backtest (quick)
python scripts/backtest_preview.py

# Parameter sweep (CSV + PNGs in reports/)
python scripts/sweep_preview.py

# Rotate logs now
python scripts/rotate_logs.py
```

---

## 16) File Map (ops-relevant)

* `config/*.yaml` — runtime knobs (run, exposure, broker, schedule, telemetry, data, logs)
* `logs/audit/ledger_YYYYMMDD.jsonl` — append-only audit (CFG/PLAN/ORDER/FILL)
* `logs/trading/daily_snapshot.csv` — exposure snapshot
* `reports/daily_report_*.html` — daily human-readable report

---

*© RegimeFlex — deterministic, EOD, audit-first.*
