# RegimeFlex Executioner Module

**Purpose:** Institutional-grade order entry logic optimized for 3x leveraged ETFs.

---

## Overview

The Executioner module provides three critical components for professional-grade execution:

1. **Morning Rush Filter** - Prevents trades in first 15 minutes (9:30-9:45 AM EST)
2. **Liquidity Check** - Delays entry by 30 minutes if volume is 2 SD below mean
3. **Leverage Decay Logger** - Tracks volatility decay daily to ensure strategy edge

---

## 1. Morning Rush Filter

### Configuration: `config/schedule.yaml`

```yaml
morning_rush:
  enabled: true
  start: '09:30'
  end: '09:45'
  timezone: America/New_York
  block_all_trades: true  # Block all trades during this window
```

### How It Works

**Institutional-Grade Entry:** Prevents any trades from being executed in the first 15 minutes of market open (9:30 AM–9:45 AM EST) to avoid the 'Opening Gap' volatility.

3x leveraged ETFs like TQQQ/SQQQ are particularly vulnerable to:
- Opening gap volatility
- Low liquidity at market open
- Price discovery chaos in first 15 minutes

### Integration

**Location:** `engine/runner.py` (before order execution)

```python
mr_check = morning_rush_check(sch_cfg)
if mr_check.get("blocked"):
    # Block all trades, return early
    crumbs.update({"no_op": True, "no_op_reason": "MORNING_RUSH"})
```

### Example Behavior

```
09:30 AM EST → Morning Rush Filter active → Trade blocked
09:45 AM EST → Morning Rush cleared → Trade proceeds
```

### Benefits

- ✅ Avoids opening gap volatility
- ✅ Waits for price discovery to stabilize
- ✅ Reduces slippage from low liquidity
- ✅ Configurable time window

---

## 2. Liquidity Check

### Configuration: `config/metrics.yaml` (implicit)

The liquidity check uses ADV (Average Daily Volume) statistics calculated from historical data.

### How It Works

**Institutional-Grade Entry:** Before entering a position, check the 'Average Daily Volume' (ADV). If the current volume is 2 standard deviations below the mean, delay the entry by 30 minutes to wait for better liquidity.

**Algorithm:**
1. Calculate rolling 20-day ADV mean and standard deviation
2. Compare current volume to historical distribution
3. If Z-score < -2.0 (2 SD below mean) → Delay entry by 30 minutes
4. Return `retry_after` timestamp for scheduled retry

### Integration

**Location:** `engine/runner.py` (before order execution)

```python
z_check = check_zscore_liquidity(
    symbol, current_vol, history_df,
    window=20,
    z_thresh=-2.0,
    delay_minutes=30
)

if z_check.get("blocked"):
    # Delay entry, set retry timestamp
    crumbs.update({
        "no_op": True,
        "no_op_reason": "LIQUIDITY_DELAY",
        "liquidity_retry_after": z_check.get("retry_after")
    })
```

### Example Behavior

**Normal Liquidity:**
```
Current Volume: 50M shares
ADV Mean: 45M shares
ADV Std: 2M shares
Z-Score: +2.5 → Trade proceeds
```

**Low Liquidity:**
```
Current Volume: 35M shares
ADV Mean: 45M shares
ADV Std: 5M shares
Z-Score: -2.0 → Delay entry by 30 minutes
Retry After: 2026-01-09T14:30:00Z
```

### Benefits

- ✅ Prevents entry during low-volume periods
- ✅ Reduces slippage risk
- ✅ 30-minute delay allows liquidity to build
- ✅ Returns retry timestamp for scheduling

---

## 3. Leverage Decay Logger

### Configuration: `engine/decay.py` (implicit)

### How It Works

**Institutional-Grade Entry:** Create a function that calculates and logs 'Volatility Decay' on TQQQ/SQQQ holdings daily, comparing our performance against the raw QQQ index to ensure the 'Swing' strategy is actually outperforming.

**Decay Calculation:**
```
Decay = (Leveraged Return) - (Leverage * Index Return)
```

**Metrics Tracked:**
- Daily tracking error (basis points)
- Period decay percentage
- Actual vs theoretical growth
- Outperformance indicator

### Integration

**Location:** `engine/runner.py` (after order planning, before execution)

```python
decay_stats = {}
d_long = log_volatility_decay(
    "TQQQ", tqqq_df, "QQQ", qqq_df,
    leverage=3.0,
    save_daily=True,
    lookback=20
)
decay_stats["TQQQ"] = d_long
```

### Daily Logs

**Location:** `logs/decay/{SYMBOL}_decay_{YYYY-MM-DD}.json`

```json
{
  "symbol": "TQQQ",
  "index": "QQQ",
  "entries": [
    {
      "symbol": "TQQQ",
      "index": "QQQ",
      "lookback_days": 20,
      "leverage": 3.0,
      "daily_tracking_error_bps": -5.2,
      "period_decay_pct": -1.2,
      "outperforming": true,
      "edge_working": true,
      "timestamp": "2026-01-09T14:00:00Z"
    }
  ]
}
```

### Example Output

**Outperforming Strategy:**
```
Decay TQQQ: -5.2bps daily error | -1.2% period drift (20d) | ✅ OUTPERFORMING
```

**Underperforming Strategy:**
```
Decay TQQQ: +8.5bps daily error | +2.3% period drift (20d) | ⚠️ UNDERPERFORMING
⚠️ Strategy Edge Warning: TQQQ decay 2.3% suggests strategy may not be outperforming
```

### Benefits

- ✅ Daily tracking of volatility decay
- ✅ Performance comparison vs raw index
- ✅ Alerts if strategy edge is eroding
- ✅ Historical decay logs for analysis

---

## Complete Execution Flow

```
┌─────────────────────────────────────┐
│  Order Intent Generated              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  1. Morning Rush Filter              │
│     - Check if 9:30-9:45 AM EST      │
│     - Block if in window              │
└──────────────┬──────────────────────┘
               │ (if outside window)
               ▼
┌─────────────────────────────────────┐
│  2. Liquidity Check                   │
│     - Calculate ADV Z-score           │
│     - If < -2.0 SD → Delay 30 min    │
│     - Return retry_after timestamp    │
└──────────────┬──────────────────────┘
               │ (if liquidity OK)
               ▼
┌─────────────────────────────────────┐
│  3. Order Execution                   │
│     - Place orders                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. Leverage Decay Logger             │
│     - Calculate decay vs index        │
│     - Log daily performance           │
│     - Alert if underperforming        │
└─────────────────────────────────────┘
```

---

## Configuration

### Full `config/schedule.yaml` Example

```yaml
morning_rush:
  enabled: true
  start: '09:30'
  end: '09:45'
  timezone: America/New_York
  block_all_trades: true
```

### Liquidity Check Parameters

**Function:** `check_zscore_liquidity()`

- `window`: Rolling window for ADV (default: 20 days)
- `z_thresh`: Z-score threshold (default: -2.0)
- `delay_minutes`: Delay duration (default: 30 minutes)

### Decay Logger Parameters

**Function:** `log_volatility_decay()`

- `lookback`: Days to look back (default: 20)
- `leverage`: Leverage factor (default: 3.0)
- `save_daily`: Save daily logs (default: True)
- `log_dir`: Log directory (default: "logs/decay")

---

## Usage Examples

### Morning Rush Check

```python
from engine.window_gate import morning_rush_check
from engine.config import Config

cfg = Config(".")
schedule_cfg = cfg._load_yaml("config/schedule.yaml") or {}

mr_check = morning_rush_check(schedule_cfg)
if mr_check.get("blocked"):
    print(f"Blocked: {mr_check['reason']}")
    print(f"Minutes remaining: {mr_check.get('minutes_remaining')}")
```

### Liquidity Check

```python
from engine.liquidity import check_zscore_liquidity
import pandas as pd

# Get current volume and history
current_vol = 35_000_000  # 35M shares
history_df = pd.DataFrame(...)  # Historical data

z_check = check_zscore_liquidity(
    "TQQQ", current_vol, history_df,
    window=20,
    z_thresh=-2.0,
    delay_minutes=30
)

if z_check.get("blocked"):
    print(f"Delayed: {z_check['reason']}")
    print(f"Retry after: {z_check['retry_after']}")
    print(f"Z-Score: {z_check['z_score']}")
    print(f"Current vs ADV: {z_check['current_vs_adv_pct']}%")
```

### Decay Logger

```python
from engine.decay import log_volatility_decay
import pandas as pd

tqqq_df = pd.DataFrame(...)  # TQQQ data
qqq_df = pd.DataFrame(...)    # QQQ data

decay = log_volatility_decay(
    "TQQQ", tqqq_df, "QQQ", qqq_df,
    leverage=3.0,
    save_daily=True,
    lookback=20
)

print(f"Daily tracking error: {decay['daily_tracking_error_bps']} bps")
print(f"Period decay: {decay['period_decay_pct']}%")
print(f"Outperforming: {decay['outperforming']}")
```

---

## Performance Monitoring

### Daily Decay Logs

**Location:** `logs/decay/`

**Files:**
- `TQQQ_decay_2026-01-09.json`
- `PSQ_decay_2026-01-09.json`

**Analysis:**
```python
import json
from pathlib import Path

decay_file = Path("logs/decay/TQQQ_decay_2026-01-09.json")
with open(decay_file) as f:
    data = json.load(f)
    
for entry in data["entries"]:
    print(f"{entry['timestamp']}: {entry['daily_tracking_error_bps']} bps")
```

### Strategy Edge Monitoring

**Alert Conditions:**
- `outperforming: false` AND `period_decay_pct > 2.0%`
- Suggests strategy edge may be eroding
- Triggers warning log

**Action Items:**
- Review recent trades
- Check if regime detection is working
- Consider reducing position sizes
- Review risk parameters

---

## Integration Points

### 1. Runner (`engine/runner.py`)
- ✅ Morning Rush check before order planning
- ✅ Liquidity check before order execution
- ✅ Decay logger after order planning

### 2. Window Gate (`engine/window_gate.py`)
- ✅ `morning_rush_check()` function
- ✅ Configurable time window
- ✅ Timezone-aware

### 3. Liquidity (`engine/liquidity.py`)
- ✅ `check_zscore_liquidity()` function
- ✅ ADV calculation
- ✅ Z-score calculation
- ✅ Delay mechanism with retry timestamp

### 4. Decay (`engine/decay.py`)
- ✅ `log_volatility_decay()` function
- ✅ Daily log persistence
- ✅ Performance comparison
- ✅ Outperformance tracking

---

## Summary

✅ **Morning Rush Filter** - Blocks trades 9:30-9:45 AM EST  
✅ **Liquidity Check** - Delays entry 30 min if volume < 2 SD below mean  
✅ **Leverage Decay Logger** - Tracks decay daily, ensures strategy edge  

All three components are **fully integrated** and **production-ready**.

The Executioner module ensures RegimeFlex trades like a bank, not a retail trader, with institutional-grade entry logic optimized for 3x leveraged ETFs.

