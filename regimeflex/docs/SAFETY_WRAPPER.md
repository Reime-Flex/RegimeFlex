# RegimeFlex Safety Wrapper (Shield)

**Purpose:** Advanced error handling and safety mechanisms to prevent costly mistakes during market chaos or network issues.

---

## Overview

The Safety Wrapper provides three critical layers of protection:

1. **Stale Data Check** - Abort trades if data is older than 60 seconds
2. **Slippage Protection** - Convert market orders to limit orders with 0.05% buffer
3. **Duplicate Trade Prevention** - State lock file prevents double-dipping

---

## 1. Stale Data Check

### Configuration: `config/safety.yaml`

```yaml
stale_data:
  enabled: true
  threshold_seconds: 60              # Abort trade if data older than 60 seconds
  alert_channel: "telegram"          # telegram | discord | log_only
```

### How It Works

Before any order is placed, the system:
1. Extracts the timestamp from the latest Polygon data bar
2. Compares it with the current system time
3. If data is older than 60 seconds → **abort trade** and alert user
4. Sends warning alert via Guardian module (Telegram/Discord)

### Integration

**Location:** `engine/runner.py` (before order execution)

```python
# Check freshness of Polygon data
last_ts = long_df.index[-1]
is_fresh, age_seconds, msg = safety.validate_freshness(last_ts, raise_on_stale=True)
```

### Example Behavior

```
✅ Data fresh: 30.0s old  → Trade proceeds
⛔ STALE DATA: 90.0s old > 60s threshold  → Trade aborted
```

### Error Handling

- Raises `StaleDataError` if data is stale
- Sends Guardian warning alert
- Sets `no_op_reason: "STALE_DATA_SHIELD"` in breadcrumbs
- Aborts entire trading cycle

---

## 2. Slippage Protection

### Configuration: `config/safety.yaml`

```yaml
slippage_protection:
  enabled: true
  buffer_pct: 0.0005                 # 0.05% buffer for limit orders
  force_limit_orders: true           # Convert all market orders to limit orders
```

### How It Works

**Before order execution:**
1. System checks if order is a market order
2. If market order → converts to limit order with protective buffer
3. Calculates limit price:
   - **BUY**: `mid_price * (1 + 0.05%)` - willing to pay slightly more
   - **SELL**: `mid_price * (1 - 0.05%)` - willing to receive slightly less
4. Ensures we aren't "chewed up" by the spread during TQQQ volatility

### Integration

**Location:** `engine/exec_alpaca.py` (before sending orders)

```python
# Apply slippage protection to payloads
if safety and mid_prices:
    protected_p = safety.protect_order(p.copy(), mid_price)
```

### Example Behavior

**Market Order:**
```
Original: BUY 100 shares @ MARKET
Protected: BUY 100 shares @ LIMIT $100.05 (mid=$100.00, buffer=0.05%)
```

**Limit Order Adjustment:**
```
Original: BUY @ $99.90 (too aggressive)
Protected: BUY @ $100.05 (ensures fill while protecting against slippage)
```

### Benefits

- ✅ Prevents execution at unfavorable prices during volatility
- ✅ Ensures fills while protecting against spread
- ✅ Works for both market and existing limit orders

---

## 3. Duplicate Trade Prevention

### Configuration: `config/safety.yaml`

```yaml
duplicate_prevention:
  enabled: true
  state_file: "data/trading_state.json"
  lock_timeout_seconds: 300          # Auto-release stale locks after 5 minutes
  check_on_startup: true             # Validate and clean state on bot startup
```

### How It Works

**Before placing any order:**
1. System checks `data/trading_state.json` for active orders
2. Looks for existing orders with same `symbol` + `side` combination
3. If found → **block order** and raise `OrderLockError`
4. If not found → acquire lock, place order, release lock after completion

### State File Structure

```json
{
  "version": 1,
  "last_updated": "2026-01-09T12:00:00Z",
  "active_orders": [
    {
      "order_key": "TQQQ_BUY_20260109T120000Z",
      "symbol": "TQQQ",
      "side": "BUY",
      "qty": 100,
      "created_at": "2026-01-09T12:00:00Z",
      "status": "pending",
      "limit_price": 100.05
    }
  ],
  "completed_orders": [...],
  "failed_orders": [...]
}
```

### Integration

**Location:** `engine/exec_alpaca.py` (wraps order execution)

```python
# Acquire lock before placing order
with safety.order_lock(symbol, side, qty, limit_price):
    # Place order
    result = executor.place_order(...)
# Lock automatically released after execution
```

### Features

- ✅ **File locking** - Uses `fcntl` on Unix/Linux for thread safety
- ✅ **Atomic operations** - Temp file + rename for safe writes
- ✅ **Stale lock cleanup** - Auto-releases locks older than 5 minutes
- ✅ **Startup validation** - Cleans stale locks on bot startup
- ✅ **Windows compatible** - Falls back gracefully on Windows

### Example Behavior

**First Order:**
```
🔒 Order lock acquired: TQQQ_BUY_20260109T120000Z
[Order placed successfully]
🔓 Order lock released: TQQQ_BUY_20260109T120000Z (completed)
```

**Duplicate Attempt:**
```
⛔ DUPLICATE PREVENTED: Cannot place BUY order for TQQQ: 
   Active order already exists (key=TQQQ_BUY_20260109T120000Z)
   This prevents double-dipping due to loop errors.
```

---

## Complete Safety Flow

```
┌─────────────────────────────────────┐
│  Order Intent Generated              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  1. Stale Data Check                 │
│     - Compare Polygon timestamp      │
│     - Abort if > 60 seconds old     │
└──────────────┬──────────────────────┘
               │ (if fresh)
               ▼
┌─────────────────────────────────────┐
│  2. Slippage Protection              │
│     - Convert market → limit         │
│     - Apply 0.05% buffer             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Duplicate Prevention             │
│     - Check trading_state.json       │
│     - Acquire lock                  │
│     - Place order                   │
│     - Release lock                  │
└─────────────────────────────────────┘
```

---

## Configuration

### Full `config/safety.yaml` Example

```yaml
# Safety Wrapper Configuration
# Shield protection for RegimeFlex execution logic

stale_data:
  enabled: true
  threshold_seconds: 60              # Abort trade if data older than 60 seconds
  alert_channel: "telegram"          # telegram | discord | log_only

slippage_protection:
  enabled: true
  buffer_pct: 0.0005                 # 0.05% buffer for limit orders
  force_limit_orders: true           # Convert all market orders to limit orders

duplicate_prevention:
  enabled: true
  state_file: "data/trading_state.json"
  lock_timeout_seconds: 300          # Auto-release stale locks after 5 minutes
  check_on_startup: true             # Validate and clean state on bot startup
```

---

## Usage Examples

### Manual Safety Check

```python
from engine.safety_wrapper import SafetyWrapper
from datetime import datetime, timezone

safety = SafetyWrapper()

# Check data freshness
data_ts = datetime.now(timezone.utc)
is_fresh, age, msg = safety.validate_freshness(data_ts)
print(msg)

# Apply slippage protection
order = {"symbol": "TQQQ", "side": "BUY", "type": "market", "qty": 100}
protected = safety.protect_order(order, mid_price=100.0)
print(protected)  # {"type": "limit", "limit_price": 100.05, ...}

# Check for duplicates
has_dup, existing = safety.check_duplicates("TQQQ", "BUY")
if has_dup:
    print(f"Duplicate blocked: {existing}")
```

### Full Order Execution with Safety

```python
from engine.safety_wrapper import wrap_order_execution

def place_order_func(**kwargs):
    # Your order placement logic
    return {"order_id": "12345"}

result = wrap_order_execution(
    order_func=place_order_func,
    symbol="TQQQ",
    side="BUY",
    qty=100,
    mid_price=100.0,
    data_timestamp=datetime.now(timezone.utc),
    order_kwargs={"type": "market"}
)
# All safety checks applied automatically!
```

---

## Error Handling

### StaleDataError

```python
try:
    safety.validate_freshness(stale_timestamp, raise_on_stale=True)
except StaleDataError as e:
    # Trade aborted, alert sent
    print(f"Stale data: {e}")
```

### OrderLockError

```python
try:
    with safety.order_lock("TQQQ", "BUY", 100):
        place_order(...)
except OrderLockError as e:
    # Duplicate prevented
    print(f"Duplicate blocked: {e}")
```

### SlippageProtectionError

```python
try:
    limit_price = calculate_limit_price(0.0, "BUY")  # Invalid price
except SlippageProtectionError as e:
    print(f"Slippage protection failed: {e}")
```

---

## Integration Points

### 1. Runner (`engine/runner.py`)
- ✅ Stale data check before order execution
- ✅ Validates both QQQ and PSQ data freshness
- ✅ Sends Guardian alerts on stale data

### 2. Executor (`engine/exec_alpaca.py`)
- ✅ Slippage protection applied to all payloads
- ✅ Duplicate prevention lock wraps order execution
- ✅ Works in both dry-run and live modes

### 3. Planner (`engine/exec_planner.py`)
- ✅ Uses safety config for slippage buffer
- ✅ Integrates with adaptive limit offset calculation

---

## Testing

### Test Stale Data Check

```bash
python3 -c "
from engine.safety_wrapper import check_data_freshness
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
stale = now - timedelta(seconds=90)

is_fresh, age, msg = check_data_freshness(stale, threshold_seconds=60)
print(msg)  # Should show stale data warning
"
```

### Test Slippage Protection

```bash
python3 -c "
from engine.safety_wrapper import calculate_limit_price

mid = 100.0
buy_limit = calculate_limit_price(mid, 'BUY', 0.0005)
print(f'BUY limit: \${buy_limit:.2f}')  # Should be $100.05
"
```

### Test Duplicate Prevention

```bash
python3 -c "
from engine.safety_wrapper import TradingStateLock

lock = TradingStateLock()
order_key = lock.acquire_lock('TQQQ', 'BUY', 100)
print(f'Lock acquired: {order_key}')

# Try duplicate
try:
    lock.acquire_lock('TQQQ', 'BUY', 100)
except Exception as e:
    print(f'Duplicate blocked: {e}')
"
```

---

## Summary

✅ **Stale Data Check** - Aborts trades if Polygon data > 60 seconds old  
✅ **Slippage Protection** - Converts market orders to limit with 0.05% buffer  
✅ **Duplicate Prevention** - State lock file prevents double-dipping  

All three safety mechanisms are **fully integrated** and **production-ready**.

The Safety Wrapper ensures that even during market chaos or network blips, the bot won't make costly mistakes due to stale data, excessive slippage, or duplicate orders.

