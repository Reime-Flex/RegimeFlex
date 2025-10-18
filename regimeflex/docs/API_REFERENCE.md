# RegimeFlex API Reference

## Core Engine API

### `engine.identity` - RegimeFlex Branding and Logging

```python
from engine.identity import RegimeFlexIdentity as RF

# Logging with RegimeFlex branding
RF.print_log("Message", "INFO")    # INFO, SUCCESS, RISK, ERROR
RF.print_log("Success message", "SUCCESS")
RF.print_log("Warning message", "RISK")
RF.print_log("Error message", "ERROR")
```

**Log Levels**:
- `INFO`: General information messages
- `SUCCESS`: Successful operations
- `RISK`: Risk-related warnings
- `ERROR`: Error conditions

### `engine.config` - Configuration Management

```python
from engine.config import Config

# Initialize configuration
cfg = Config(".")

# Access configuration sections
strategies = cfg.strategies
risk = cfg.risk
schedule = cfg.schedule
telemetry = cfg.telemetry
run = cfg.run

# Direct YAML loading
data_cfg = cfg._load_yaml("config/data.yaml")
broker_cfg = cfg._load_yaml("config/broker.yaml")
```

**Configuration Sections**:
- `strategies`: Strategy parameters and settings
- `risk`: Risk management configuration
- `schedule`: Calendar and timing settings
- `telemetry`: Notification settings
- `run`: Run parameters and report settings

### `engine.env` - Environment Variable Management

```python
from engine.env import load_env

# Load environment variables
env = load_env()

# Access API keys
alpaca_key = env.alpaca_key
alpaca_secret = env.alpaca_secret
polygon_key = env.polygon_key
telegram_bot_token = env.telegram_bot_token
telegram_chat_id = env.telegram_chat_id
```

**Environment Variables**:
- `ALPACA_KEY`: Alpaca Markets API key
- `ALPACA_SECRET`: Alpaca Markets API secret
- `POLYGON_KEY`: Polygon.io API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID

## Data Management API

### `engine.data` - Market Data Management

```python
from engine.data import get_daily_bars, get_daily_bars_with_provider
from engine.data import save_to_cache, load_from_cache, seed_cache

# Cache-only data access
qqq = get_daily_bars("QQQ")
psq = get_daily_bars("PSQ")

# Provider-routed data access
qqq = get_daily_bars_with_provider("QQQ", force_refresh=False)

# Cache management
save_to_cache("QQQ", dataframe)
cached_data = load_from_cache("QQQ")
seed_cache("QQQ", dataframe)
```

**Data Functions**:
- `get_daily_bars(symbol)`: Cache-only data access
- `get_daily_bars_with_provider(symbol, force_refresh)`: Provider-routed data
- `save_to_cache(symbol, df)`: Save data to cache
- `load_from_cache(symbol)`: Load data from cache
- `seed_cache(symbol, df)`: Seed cache with data

### `engine.data_providers` - Live Data Providers

```python
from engine.data_providers import fetch_polygon_daily, fetch_alpaca_daily

# Polygon data provider
polygon_data = fetch_polygon_daily(
    symbol="QQQ",
    days=800,
    base_url="https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}",
    api_key="your_polygon_key"
)

# Alpaca data provider
alpaca_data = fetch_alpaca_daily(
    symbol="QQQ",
    days=800,
    base_url="https://data.alpaca.markets/v2/stocks/{symbol}/bars",
    key="your_alpaca_key",
    secret="your_alpaca_secret"
)
```

**Data Providers**:
- `fetch_polygon_daily()`: Polygon.io data provider
- `fetch_alpaca_daily()`: Alpaca Markets data provider

## Technical Analysis API

### `engine.indicators` - Technical Indicators

```python
from engine.indicators import sma, ema, atr, rolling_std, realized_vol, z_score

# Simple Moving Average
sma_20 = sma(price_series, 20)

# Exponential Moving Average
ema_20 = ema(price_series, 20)

# Average True Range
atr_14 = atr(high_series, low_series, close_series, 14)

# Rolling Standard Deviation
std_20 = rolling_std(price_series, 20)

# Realized Volatility
rvol_20 = realized_vol(price_series, 20)

# Z-Score
z_score_20 = z_score(price_series, 20)
```

**Technical Indicators**:
- `sma(series, period)`: Simple Moving Average
- `ema(series, period)`: Exponential Moving Average
- `atr(high, low, close, period)`: Average True Range
- `rolling_std(series, period)`: Rolling Standard Deviation
- `realized_vol(series, period)`: Realized Volatility
- `z_score(series, period)`: Z-Score calculation

### `engine.signals` - Trading Signals

```python
from engine.signals import detect_regime, trend_signal, mr_signal
from engine.signals import RegimeState, TrendSignal, MRSignal

# Regime detection
regime = detect_regime(price_data)

# Trend following signal
trend = trend_signal(price_data, regime)

# Mean reversion signal
mr = mr_signal(price_data, regime)

# Signal objects
regime_state = RegimeState(bull=True, vix=20.0, qqq_rvol_20=0.15)
trend_signal = TrendSignal(direction="LONG", entry=True, exit=False)
mr_signal = MRSignal(direction="FLAT", entry=False, exit=True, z=-1.5)
```

**Signal Functions**:
- `detect_regime(price_data)`: Bull/bear market detection
- `trend_signal(price_data, regime)`: Trend following signals
- `mr_signal(price_data, regime)`: Mean reversion signals

## Risk Management API

### `engine.risk` - Risk Management

```python
from engine.risk import RiskConfig, compute_position_size, check_circuit_breakers

# Risk configuration
risk_cfg = RiskConfig(
    risk_budget=0.02,
    max_position_pct=0.25,
    atr_multiplier=2.0,
    vix_hard_block=35.0,
    vix_caution=25.0,
    realized_vol_block=0.05
)

# Position sizing
position_size = compute_position_size(
    price=100.0,
    atr=2.0,
    risk_budget=0.02,
    max_position_pct=0.25
)

# Circuit breaker check
breakers = check_circuit_breakers(
    vix=30.0,
    realized_vol=0.03,
    is_fomc_blackout=False,
    is_opex_day=False
)
```

**Risk Functions**:
- `compute_position_size()`: Dynamic position sizing
- `check_circuit_breakers()`: Risk-based trading blocks
- `RiskConfig`: Risk management configuration

### `engine.portfolio` - Portfolio Management

```python
from engine.portfolio import compute_target_exposure, TargetExposure

# Target exposure computation
target = compute_target_exposure(
    qqq_data=qqq_df,
    psq_data=psq_df,
    equity=25000.0,
    vix=20.0,
    cfg=risk_config,
    is_fomc_window=False,
    is_opex_day=False
)

# Target exposure object
target = TargetExposure(
    symbol="QQQ",
    direction="LONG",
    dollars=5000.0,
    shares=50.0,
    notes="Trend following signal"
)
```

**Portfolio Functions**:
- `compute_target_exposure()`: Target exposure calculation
- `TargetExposure`: Target exposure data structure

## Execution API

### `engine.exec_planner` - Order Planning

```python
from engine.exec_planner import plan_orders, OrderIntent

# Order planning
intents = plan_orders(
    current_positions={"QQQ": 50.0},
    target=target_exposure,
    current_price=100.0,
    minutes_to_close=30,
    min_trade_value=200.0,
    emergency_override=False
)

# Order intent object
intent = OrderIntent(
    symbol="QQQ",
    side="BUY",
    qty=25.0,
    order_type="limit",
    time_in_force="day",
    limit_price=99.50,
    reason="Trend following entry"
)
```

**Order Planning Functions**:
- `plan_orders()`: Order intent generation
- `OrderIntent`: Order intent data structure

### `engine.exec_alpaca` - Broker Integration

```python
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds, ALPACA_PAPER_URL, ALPACA_LIVE_URL

# Alpaca credentials
creds = AlpacaCreds(
    key="your_alpaca_key",
    secret="your_alpaca_secret",
    base_url=ALPACA_PAPER_URL  # or ALPACA_LIVE_URL
)

# Alpaca executor
executor = AlpacaExecutor(creds, dry_run=True)

# Order placement
results = executor.place_orders(intents)

# Payload generation
payloads = executor.build_payloads(intents)
```

**Broker Functions**:
- `AlpacaExecutor.place_orders()`: Order placement
- `AlpacaExecutor.build_payloads()`: Payload generation
- `AlpacaCreds`: Broker credentials

### `engine.reconcile` - Order Reconciliation

```python
from engine.reconcile import compare_intents_vs_orders

# Intent vs order reconciliation
reconciliation = compare_intents_vs_orders(intents, order_results)

# Reconciliation results
matches = reconciliation["matches"]
mismatches = reconciliation["mismatches"]
unmatched_intents = reconciliation["unmatched_intents"]
```

**Reconciliation Functions**:
- `compare_intents_vs_orders()`: Intent vs order comparison

## Storage API

### `engine.storage` - Audit Ledger

```python
from engine.storage import ENSStyleAudit

# Audit ledger
audit = ENSStyleAudit()

# Log transactions
audit.log(kind="PLAN", data=plan_data)
audit.log(kind="ORDER", data=order_data)
audit.log(kind="FILL", data=fill_data)
```

**Audit Functions**:
- `ENSStyleAudit.log()`: Transaction logging
- `ENSStyleAudit`: ENS-style audit ledger

### `engine.positions` - Position Management

```python
from engine.positions import load_positions, save_positions

# Position management
current_positions = load_positions()
save_positions(updated_positions)
```

**Position Functions**:
- `load_positions()`: Load current positions
- `save_positions()`: Save position updates

### `engine.fills` - Fill Processing

```python
from engine.fills import simulate_fills, apply_simulated_fills

# Fill simulation
fills = simulate_fills(intents, last_price=100.0)

# Fill application
updated_positions = apply_simulated_fills(current_positions, fills)
```

**Fill Functions**:
- `simulate_fills()`: Fill simulation
- `apply_simulated_fills()`: Fill application

## Utility API

### `engine.calendar` - Calendar Management

```python
from engine.calendar import is_fomc_blackout, is_opex

# Calendar checks
is_fomc = is_fomc_blackout(
    date=today,
    fomc_meetings=["2024-01-31", "2024-03-20"],
    window=(-1, 1)
)

is_opex_day = is_opex(today)
```

**Calendar Functions**:
- `is_fomc_blackout()`: FOMC blackout check
- `is_opex()`: OPEX day check

### `engine.telemetry` - Notifications

```python
from engine.telemetry import Notifier, TGCreds

# Telegram notifier
creds = TGCreds(token="bot_token", chat_id="chat_id")
notifier = Notifier(creds)

# Send notifications
notifier.send("Trading update message")
```

**Notification Functions**:
- `Notifier.send()`: Send notifications
- `TGCreds`: Telegram credentials

### `engine.report` - Report Generation

```python
from engine.report import write_daily_html

# HTML report generation
report_path = write_daily_html(
    result=run_result,
    out_dir="reports",
    filename_prefix="daily_report"
)
```

**Report Functions**:
- `write_daily_html()`: HTML report generation

### `engine.killswitch` - Emergency Controls

```python
from engine.killswitch import is_killed, enable, disable

# Kill-switch control
if is_killed():
    print("System is killed")

# Toggle kill-switch
enable()   # Enable kill-switch
disable() # Disable kill-switch
```

**Kill-Switch Functions**:
- `is_killed()`: Check kill-switch status
- `enable()`: Enable kill-switch
- `disable()`: Disable kill-switch

## Backtesting API

### `engine.backtest` - Backtesting Framework

```python
from engine.backtest import run_backtest, BTConfig, BTResult

# Backtest configuration
config = BTConfig(
    start_cash=25000.0,
    vix_assumption=20.0,
    min_trade_value=200.0,
    commission_per_share=0.005,
    fixed_fee_per_trade=0.00,
    slippage_bps=10.0,
    trend_params={},
    mr_params={"z_len": 20, "z_entry_bull": -2.0}
)

# Run backtest
result = run_backtest(qqq_data, psq_data, config)

# Backtest results
print(f"CAGR: {result.cagr:.2%}")
print(f"Max Drawdown: {result.max_dd:.2%}")
print(f"Sharpe Ratio: {result.sharpe:.2f}")
print(f"Total Trades: {result.trades}")
```

**Backtesting Functions**:
- `run_backtest()`: Run backtest simulation
- `BTConfig`: Backtest configuration
- `BTResult`: Backtest results

## Runner API

### `engine.runner` - Daily Cycle Orchestrator

```python
from engine.runner import run_daily_offline

# Daily cycle execution
result = run_daily_offline(
    equity=25000.0,
    vix=20.0,
    minutes_to_close=30,
    min_trade_value=200.0
)

# Result structure
target = result["target"]
positions_before = result["positions_before"]
intents = result["intents"]
positions_after = result["positions_after"]
breadcrumbs = result["breadcrumbs"]
```

**Runner Functions**:
- `run_daily_offline()`: Daily cycle execution

## Data Structures

### Core Data Types

```python
# Regime state
@dataclass
class RegimeState:
    bull: bool
    vix: float | None
    qqq_rvol_20: float

# Trading signals
@dataclass
class TrendSignal:
    direction: str
    entry: bool
    exit: bool
    reason: str

@dataclass
class MRSignal:
    direction: str
    entry: bool
    exit: bool
    z: float
    reason: str

# Target exposure
@dataclass
class TargetExposure:
    symbol: str
    direction: str
    dollars: float
    shares: float
    notes: str

# Order intent
@dataclass
class OrderIntent:
    symbol: str
    side: str
    qty: float
    order_type: str
    time_in_force: str
    limit_price: float | None
    reason: str

# Risk configuration
@dataclass
class RiskConfig:
    risk_budget: float = 0.02
    max_position_pct: float = 0.25
    atr_multiplier: float = 2.0
    vix_hard_block: float = 35.0
    vix_caution: float = 25.0
    realized_vol_block: float = 0.05
    fomc_blackout: bool = True
    opex_caution: bool = True

# Backtest configuration
@dataclass
class BTConfig:
    start_cash: float = 25000.0
    vix_assumption: float | None = None
    min_trade_value: float = 200.0
    commission_per_share: float = 0.0
    fixed_fee_per_trade: float = 0.0
    slippage_bps: float = 10.0
    trend_params: dict = None
    mr_params: dict = None

# Backtest results
@dataclass
class BTResult:
    cagr: float
    max_dd: float
    sharpe: float
    trades: int
    equity_series: pd.Series
```

## Error Handling

### Exception Types

```python
from engine.data import DataError, ValidationError

# Data errors
try:
    data = get_daily_bars("INVALID")
except DataError as e:
    print(f"Data error: {e}")

# Validation errors
try:
    validate_data(dataframe)
except ValidationError as e:
    print(f"Validation error: {e}")
```

**Exception Types**:
- `DataError`: Data-related errors
- `ValidationError`: Data validation errors

## Configuration Examples

### Strategy Configuration

```yaml
# config/strategies.yaml
trend:
  sma_fast: 5
  sma_slow: 20
  sma_trend: 50
  sma_long: 100
  sma_ultra: 200

mean_reversion:
  z_len: 20
  vol_confirm_mult: 1.2
  time_stop_days_bull: 5
  time_stop_days_bear: 3
  z_entry_bull: -2.0
  z_exit_bull: 0.0
  z_entry_bear: 2.0
  z_exit_bear: 0.0
```

### Risk Configuration

```yaml
# config/risk.yaml
position_sizing:
  risk_budget: 0.02
  max_position_pct: 0.25
  atr_multiplier: 2.0

circuit_breakers:
  vix_hard_block: 35.0
  vix_caution: 25.0
  realized_vol_block: 0.05
  fomc_blackout: true
  opex_caution: true
```

### Broker Configuration

```yaml
# config/broker.yaml
alpaca:
  enabled: true
  mode: "paper"
  dry_run: true
```

### Data Configuration

```yaml
# config/data.yaml
provider: "cache"
symbols: ["QQQ", "PSQ"]
lookback_days: 800
force_refresh: false

polygon:
  base_url: "https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}"

alpaca:
  base_url: "https://data.alpaca.markets/v2/stocks/{symbol}/bars"
```

---

**RegimeFlex API Reference v29** - Complete API documentation for systematic trading system with real broker integration.

*Comprehensive, precise, and production-ready.*
