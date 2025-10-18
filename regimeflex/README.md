# RegimeFlex Trading System

**Version 29** - Complete systematic trading stack with real broker integration

RegimeFlex is a production-ready, systematic trading system built with Python that implements regime-based trading strategies with comprehensive risk management, real broker integration, and professional reporting capabilities.

## 🎯 System Overview

RegimeFlex implements a sophisticated trading system that:

- **Detects Market Regimes**: Bull/bear market detection using technical indicators
- **Executes Systematic Strategies**: Trend following and mean reversion strategies
- **Manages Risk**: Dynamic position sizing with circuit breakers and risk controls
- **Integrates Real Brokers**: Live trading with Alpaca Markets (paper and live)
- **Provides Professional Reporting**: HTML reports, audit trails, and notifications
- **Supports Research**: Backtesting, parameter optimization, and visualization

## 🏗️ Architecture

### Core Components

```
regimeflex/
├── engine/                 # Core trading engine
│   ├── identity.py        # RegimeFlex branding and logging
│   ├── config.py         # YAML configuration management
│   ├── env.py            # Environment variable handling
│   ├── data.py          # Market data with caching and validation
│   ├── indicators.py      # Technical indicators (SMA, EMA, ATR, etc.)
│   ├── signals.py        # Regime detection and trading signals
│   ├── risk.py           # Risk management and circuit breakers
│   ├── portfolio.py      # Target exposure computation
│   ├── exec_planner.py   # Order planning and execution logic
│   ├── exec_alpaca.py    # Alpaca broker integration
│   ├── reconcile.py      # Intent vs order reconciliation
│   ├── positions.py      # Position management and storage
│   ├── fills.py          # Fill simulation and processing
│   ├── storage.py        # ENS-style audit ledger
│   ├── calendar.py       # FOMC and OPEX calendar guard
│   ├── telemetry.py      # Telegram notifications
│   ├── report.py         # HTML report generation
│   ├── killswitch.py     # Emergency kill-switch system
│   ├── data_providers.py # Live data providers (Polygon, Alpaca)
│   ├── backtest.py       # Backtesting framework
│   └── runner.py         # Daily cycle orchestrator
├── config/               # Configuration files
│   ├── strategies.yaml   # Strategy parameters
│   ├── risk.yaml         # Risk management settings
│   ├── schedule.yaml     # Calendar and timing
│   ├── telemetry.yaml    # Notification settings
│   ├── run.yaml          # Run parameters and reports
│   ├── data.yaml         # Data provider configuration
│   ├── broker.yaml       # Broker integration settings
│   └── kill_switch.flag  # Emergency kill-switch file
├── scripts/              # Execution scripts
│   ├── run_offline_from_config.py  # Config-driven daily run
│   ├── broker_place_preview.py     # Order placement testing
│   ├── fetch_live_to_cache.py      # Data ingestion
│   ├── sweep_preview.py            # Parameter optimization
│   ├── backtest_preview.py         # Backtesting demonstration
│   └── kill_switch.py              # Kill-switch toggle
├── data/                 # Data storage
│   └── cache/            # CSV data cache
├── logs/                 # Audit and logging
│   └── audit/            # ENS-style audit ledger
├── reports/              # Generated reports
│   ├── daily_report_*.html        # HTML daily reports
│   ├── sweep_results.csv          # Parameter optimization results
│   ├── sweep_scatter_mar.png      # Performance scatter plots
│   └── sweep_pivot_mar.png        # Parameter sensitivity heatmaps
└── branding/             # RegimeFlex design system
    ├── fonts/            # Typography assets
    └── logos/            # Logo assets
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Virtual environment (recommended)
- Alpaca Markets account (for live trading)
- Telegram bot (for notifications, optional)

### Installation

```bash
# Clone and setup
git clone <repository>
cd regimeflex
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp config/env.example .env
# Edit .env with your API keys

# Test the system
python scripts/run_offline_from_config.py
```

### Configuration

1. **Environment Variables** (`.env`):
   ```bash
   ALPACA_KEY=your_alpaca_key
   ALPACA_SECRET=your_alpaca_secret
   POLYGON_KEY=your_polygon_key
   TELEGRAM_BOT_TOKEN=your_telegram_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

2. **Broker Settings** (`config/broker.yaml`):
   ```yaml
   alpaca:
     enabled: true        # Enable broker integration
     mode: "paper"        # "paper" | "live"
     dry_run: true        # Master safety switch
   ```

3. **Data Provider** (`config/data.yaml`):
   ```yaml
   provider: "cache"      # "cache" | "polygon" | "alpaca"
   symbols: ["QQQ", "PSQ"]
   lookback_days: 800
   force_refresh: false
   ```

## 📊 Core Features

### 1. Regime-Based Trading

**Regime Detection**:
- Bull/bear market identification using technical indicators
- VIX-based volatility regime detection
- Realized volatility analysis
- Adaptive strategy selection based on market regime

**Trading Strategies**:
- **Trend Following**: SMA-based trend detection with regime adaptation
- **Mean Reversion**: Z-score based mean reversion with volume confirmation
- **Regime Adaptation**: Strategy parameters adjust based on market regime

### 2. Risk Management

**Dynamic Position Sizing**:
- ATR-based position sizing
- Risk budget allocation
- Maximum position caps
- Regime-adjusted sizing

**Circuit Breakers**:
- VIX-based volatility blocks
- Realized volatility limits
- FOMC blackout periods
- OPEX caution periods

### 3. Real Broker Integration

**Alpaca Markets Integration**:
- Paper trading environment (default)
- Live trading capability
- Order placement and management
- Real-time position tracking

**Safety Features**:
- Dry-run mode (default)
- Kill-switch emergency stop
- Config-driven broker control
- Comprehensive error handling

### 4. Professional Reporting

**HTML Reports**:
- Daily trading reports
- Position summaries
- Order history
- Performance metrics

**Audit Trail**:
- ENS-style append-only ledger
- RFC3339 timestamps
- Deterministic transaction hashes
- Complete order history

### 5. Research and Optimization

**Backtesting Framework**:
- Historical data processing
- Transaction cost modeling
- Slippage simulation
- Performance metrics calculation

**Parameter Optimization**:
- Grid search capabilities
- Performance ranking
- CSV export
- Visualization plots

## 🔧 Configuration Guide

### Strategy Configuration (`config/strategies.yaml`)

```yaml
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

### Risk Configuration (`config/risk.yaml`)

```yaml
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

### Run Configuration (`config/run.yaml`)

```yaml
equity: 25000.0
vix_assumption: 20.0
minutes_to_close: 28
min_trade_value: 200.0

report:
  enabled: true
  out_dir: "reports"
  filename_prefix: "daily_report"
  include_positions: true
  include_intents: true
  include_breadcrumbs: true
```

## 🎮 Usage Examples

### Daily Trading Run

```bash
# Run with current configuration
python scripts/run_offline_from_config.py

# Output:
# - Target exposure calculation
# - Order planning
# - Broker integration (if enabled)
# - HTML report generation
# - Telegram notifications
```

### Data Management

```bash
# Fetch live data and update cache
python scripts/fetch_live_to_cache.py

# Test different data providers
# Edit config/data.yaml: provider: "polygon"
python scripts/fetch_live_to_cache.py
```

### Parameter Optimization

```bash
# Run parameter sweep
python scripts/sweep_preview.py

# Output:
# - CSV results: reports/sweep_results.csv
# - Scatter plot: reports/sweep_scatter_mar.png
# - Heatmap: reports/sweep_pivot_mar.png
```

### Backtesting

```bash
# Run backtest with transaction costs
python scripts/backtest_preview.py

# Output:
# - Performance metrics
# - Equity curve
# - Trade statistics
```

### Emergency Controls

```bash
# Enable kill-switch (emergency stop)
python scripts/kill_switch.py

# Disable kill-switch
python scripts/kill_switch.py
```

## 📈 Performance Metrics

### Backtesting Metrics

- **CAGR**: Compound Annual Growth Rate
- **Max Drawdown**: Maximum peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns
- **MAR**: CAGR / Max Drawdown ratio
- **Win Rate**: Percentage of profitable trades
- **Average Trade**: Mean profit/loss per trade

### Risk Metrics

- **Position Sizing**: ATR-based dynamic sizing
- **Risk Budget**: Maximum risk per trade
- **Circuit Breakers**: Volatility and calendar-based blocks
- **Regime Adjustment**: Risk scaling based on market regime

## 🔒 Safety Features

### Kill-Switch System

- **File-based Control**: `config/kill_switch.flag`
- **Hard Stop**: Immediate system shutdown
- **No Side Effects**: Clean abort without partial operations
- **Easy Toggle**: Simple script for control

### Broker Safety

- **Dry-Run Default**: No live orders without explicit configuration
- **Paper Trading**: Safe testing environment
- **Config-Driven**: YAML-based broker control
- **Error Handling**: Comprehensive API error management

### Risk Controls

- **Circuit Breakers**: Multiple risk-based blocks
- **Position Limits**: Maximum position sizing
- **Regime Adaptation**: Risk scaling based on market conditions
- **Calendar Guard**: FOMC and OPEX protection

## 📊 Data Management

### Data Providers

- **Cache**: Local CSV data (default)
- **Polygon**: Live market data
- **Alpaca**: Broker data integration

### Data Validation

- **Non-empty Check**: Ensures data availability
- **Column Validation**: Required OHLCV columns
- **Sorting Check**: Chronological order validation
- **Recency Check**: Data freshness validation
- **Volume Check**: Suspicious volume detection

### Caching System

- **Intelligent Caching**: Cache-first with live fallback
- **Data Normalization**: Consistent format across providers
- **Validation Pipeline**: All data validated before caching
- **Error Handling**: Graceful fallback to cache

## 🎨 Design System

### RegimeFlex Branding

- **Color Palette**: Professional blue and neutral tones
- **Typography**: Inter font family for readability
- **Logging**: Colorized console output with branding
- **Reports**: Clean, modern HTML styling

### Visual Identity

- **Minimalist Design**: Clean, uncluttered interface
- **Trust-Focused**: Professional appearance
- **ENS-Inspired**: Ethereum Name Service aesthetic
- **Consistent Branding**: Unified visual language

## 🔧 Development

### Project Structure

```
regimeflex/
├── engine/          # Core trading engine (29 modules)
├── config/          # Configuration files (7 files)
├── scripts/         # Execution scripts (6 scripts)
├── data/            # Data storage
├── logs/            # Audit and logging
├── reports/         # Generated reports
└── branding/        # Design system assets
```

### Key Dependencies

```python
# Core dependencies
pandas>=2.0.0          # Data manipulation
requests>=2.31.0        # HTTP requests
pyyaml>=6.0            # Configuration
python-dotenv>=1.0.0   # Environment variables
colorama>=0.4.0        # Colored logging
matplotlib>=3.5.0      # Visualization
python-telegram-bot>=20.0  # Notifications
```

### Testing

```bash
# Test individual components
python -c "from engine.identity import RegimeFlexIdentity as RF; RF.print_log('Test', 'INFO')"

# Test data providers
python scripts/fetch_live_to_cache.py

# Test broker integration
python scripts/broker_place_preview.py

# Test parameter optimization
python scripts/sweep_preview.py
```

## 📚 API Reference

### Core Engine Modules

#### `engine.identity`
RegimeFlex branding and logging system.

```python
from engine.identity import RegimeFlexIdentity as RF

RF.print_log("Message", "INFO")    # INFO, SUCCESS, RISK, ERROR
```

#### `engine.config`
YAML configuration management.

```python
from engine.config import Config

cfg = Config(".")
strategies = cfg.strategies
risk = cfg.risk
```

#### `engine.data`
Market data with caching and validation.

```python
from engine.data import get_daily_bars, get_daily_bars_with_provider

# Cache-only data
qqq = get_daily_bars("QQQ")

# Provider-routed data
qqq = get_daily_bars_with_provider("QQQ")
```

#### `engine.signals`
Regime detection and trading signals.

```python
from engine.signals import detect_regime, trend_signal, mr_signal

regime = detect_regime(price_data)
trend = trend_signal(price_data, regime)
mr = mr_signal(price_data, regime)
```

#### `engine.risk`
Risk management and circuit breakers.

```python
from engine.risk import RiskConfig, compute_position_size

risk_cfg = RiskConfig()
position_size = compute_position_size(price, atr, risk_cfg)
```

#### `engine.exec_alpaca`
Alpaca broker integration.

```python
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds

creds = AlpacaCreds(key="...", secret="...")
executor = AlpacaExecutor(creds, dry_run=True)
results = executor.place_orders(intents)
```

### Configuration Files

#### `config/strategies.yaml`
Strategy parameters and settings.

#### `config/risk.yaml`
Risk management configuration.

#### `config/broker.yaml`
Broker integration settings.

#### `config/data.yaml`
Data provider configuration.

#### `config/run.yaml`
Run parameters and report settings.

## 🚨 Emergency Procedures

### Kill-Switch Activation

```bash
# Enable kill-switch (emergency stop)
python scripts/kill_switch.py

# System will abort before any trading actions
# No orders will be placed
# No positions will be changed
```

### Broker Safety

```bash
# Ensure dry-run mode
# Edit config/broker.yaml:
alpaca:
  dry_run: true

# Disable broker integration
alpaca:
  enabled: false
```

### Data Safety

```bash
# Use cache-only data
# Edit config/data.yaml:
provider: "cache"

# Force refresh disabled
force_refresh: false
```

## 📞 Support

### Troubleshooting

1. **Configuration Issues**: Check YAML syntax and file paths
2. **Data Issues**: Verify data provider credentials and cache
3. **Broker Issues**: Check API keys and network connectivity
4. **Performance Issues**: Review risk settings and position sizing

### Logging

- **Console Output**: Colorized logging with RegimeFlex branding
- **Audit Trail**: Complete order history in `logs/audit/`
- **HTML Reports**: Daily reports in `reports/`
- **Telegram**: Real-time notifications (if configured)

### Monitoring

- **Kill-Switch Status**: Check `config/kill_switch.flag`
- **Broker Status**: Monitor `config/broker.yaml`
- **Data Freshness**: Check cache timestamps
- **Position Tracking**: Monitor position changes

---

**RegimeFlex Trading System v29** - Complete systematic trading stack with real broker integration, professional reporting, and comprehensive safety features.

*Built with precision, designed for trust, engineered for performance.*