# RegimeFlex: Automated TQQQ/SQQQ Swing Trading System

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/status-production--ready-green.svg)](https://github.com/Reime-Flex/RegimeFlex)

**RegimeFlex** is a systematic trading system that implements regime-switching swing trading strategies for 3x leveraged ETFs (TQQQ/SQQQ) with institutional-grade risk management and execution safeguards.

---

## The Strategy: Regime-Switching Alpha

RegimeFlex employs a **regime-switching** philosophy that adapts trading behavior based on detected market conditions. The system analyzes the QQQ index to determine whether the market is in a **bull**, **bear**, or **neutral** regime, then adjusts strategy and instrument selection accordingly.

### Regime Detection Logic

The system uses a **200-day simple moving average (SMA)** of QQQ as the primary regime indicator, with hysteresis to prevent rapid regime flip-flopping:

- **Bull Regime**: QQQ close > 200-day SMA (with 2% buffer band and 2-day confirmation)
- **Bear Regime**: QQQ close < 200-day SMA (with 2% buffer band and 2-day confirmation)
- **Neutral**: Transition periods or insufficient confirmation

### Strategy Behavior by Regime

| Regime | Instrument | Strategy Type | Signal Logic | Position Sizing |
|--------|-----------|---------------|-------------|-----------------|
| **Bull** | TQQQ (3x Long QQQ) | Trend Following | Entry: Close > SMA(200) AND SMA(20) > SMA(50) AND SMA(5) > SMA(20)<br>Exit: Close < SMA(100) OR SMA(20) < SMA(50) | Dynamic based on ATR, volatility dampener, leverage decay adjustment |
| **Bear** | SQQQ/PSQ (3x Short QQQ) | Mean Reversion | Entry: Z-score < -2.0 (oversold bounce)<br>Exit: Z-score > 0.0 OR time stop (5 days) | Reduced sizing with volatility scaling |
| **Neutral** | CASH | No Position | All signals blocked | N/A |

### Signal Combination Logic

- **Bull Regime**: Trend signal takes priority; mean-reversion can confirm but not override
- **Bear Regime**: Mean-reversion signals drive short positions via SQQQ/PSQ
- **Risk Filters**: VIX < 30, 50-day realized volatility < 40%, FOMC blackouts respected

---

## Core Objectives

RegimeFlex is designed with explicit performance targets based on historical backtesting and regime analysis:

| Metric | Target | Rationale |
|--------|--------|-----------|
| **CAGR** | ~40% annually | Achieved through regime-adaptive position sizing and leverage amplification |
| **Maximum Drawdown** | ~33% | Controlled via dynamic position sizing, volatility dampeners, and circuit breakers |
| **Sharpe Ratio** | >1.5 | Risk-adjusted returns optimized through regime detection and volatility scaling |
| **Win Rate** | 55-60% | Balanced through trend-following (bull) and mean-reversion (bear) strategies |

**⚠️ Important**: These are historical targets based on backtesting. Past performance does not guarantee future results. Trading involves substantial risk of loss.

---

## Technical Stack

### Core Technologies

- **Language**: Python 3.12+ (type hints, modern async support)
- **Data Processing**: pandas 2.0+, numpy 1.24+ (time-series analysis, technical indicators)
- **Market Data**: Polygon.io (primary), Alpaca Markets (fallback)
- **Brokerage**: Alpaca Markets API (paper & live trading)
- **Process Management**: PM2 (ecosystem-based process monitoring)
- **Notifications**: Telegram Bot API, Discord Webhooks (optional)
- **Configuration**: YAML-based (PyYAML 6.0+)

### Key Dependencies

```python
# Core
pandas>=2.0.0          # Time-series data manipulation
numpy>=1.24.0          # Numerical computations
requests>=2.31.0       # HTTP client for APIs

# Market Data & Calendars
pandas-market-calendars>=4.4.0  # US market holiday detection

# Configuration & Environment
pyyaml>=6.0            # YAML configuration parsing
python-dotenv>=1.0.0   # Environment variable management

# Notifications
python-telegram-bot>=20.0  # Telegram alerts
twilio>=8.0.0          # SMS emergency alerts (optional)

# System Monitoring
psutil>=5.9.0          # CPU, memory, disk monitoring

# Web Framework
flask>=2.3.0           # Health check endpoints
```

---

## Safety & Governance: Hardened Production System

RegimeFlex implements **institutional-grade safeguards** to protect capital and ensure reliable operation. All features have been validated through comprehensive pre-flight audit and stress testing.

### 1. Anti-Look-Ahead Bias Protection

**Problem**: Using incomplete daily bars (today's close) for signal generation creates look-ahead bias.

**Solution**: 
- `bar_completeness.py` module verifies bar completeness before use
- Automatically falls back to T-1 (yesterday's) bar if current bar is incomplete
- All signal generation and position sizing uses verified complete bars only

```python
# Example: Safe price extraction
safe_price, is_safe, reason = get_safe_price(df, use_t1_if_incomplete=True)
```

### 2. Slippage-Protected Limit Orders

**Problem**: Market orders can execute at unfavorable prices during volatility spikes.

**Solution**:
- All market orders automatically converted to limit orders
- 0.05% buffer above/below mid-price (adaptive based on ATR)
- Maximum 2% offset cap to prevent excessive slippage
- Mid-price calculation from bid/ask or last trade

**Implementation**: `engine/safety_wrapper.py` → `apply_slippage_protection()`

### 3. Automated Kill Switch

**Problem**: Need immediate emergency stop without code deployment.

**Solution**:
- File-based kill switch: `data/state/kill_switch.json`
- Instant activation: `python scripts/kill_switch.py activate "Emergency"`
- All trading logic returns FLAT immediately when active
- Checked before every run (before acquiring run lock)

**Usage**:
```bash
# Activate kill switch
python scripts/kill_switch.py activate "Market volatility spike detected"

# Check status
python scripts/kill_switch.py status

# Deactivate
python scripts/kill_switch.py deactivate
```

### 4. Morning Rush Filter

**Problem**: Opening gap volatility (9:30-9:45 AM EST) can cause poor fills.

**Solution**:
- Blocks all trades during first 15 minutes of market open
- Configurable via `config/schedule.yaml`
- Returns early with "MORNING_RUSH" no-op reason
- Sends heartbeat notification indicating wait period

**Configuration**:
```yaml
morning_rush:
  enabled: true
  start: '09:30'
  end: '09:45'
  timezone: America/New_York
  block_all_trades: true
```

### 5. Leverage Decay Adjustment

**Problem**: 3x leveraged ETFs decay in choppy/sideways markets, eroding returns.

**Solution**:
- Daily volatility decay tracking: `engine/decay.py`
- Compares TQQQ/SQQQ performance vs QQQ index
- Automatically reduces position sizes by up to 30% when decay > 1% over 20 days
- Alerts when strategy underperforms significantly (>2% decay)

**Metrics Tracked**:
- Daily tracking error (basis points)
- Period decay percentage
- Outperformance flag
- Historical decay logs (last 30 days)

### 6. Execution Run Lock

**Problem**: Concurrent execution can cause double-sizing or race conditions.

**Solution**:
- File-based run lock: `data/state/run.lock`
- Prevents concurrent execution of trading loop
- Stale lock detection (5-minute timeout)
- Atomic file operations with `fcntl` locking (Unix/Linux)

### 7. Regime Hysteresis

**Problem**: Rapid regime flip-flopping causes excessive trading and slippage.

**Solution**:
- 2% buffer band around 200-day SMA
- Requires 2 consecutive days above/below threshold to switch regimes
- Maintains current regime during buffer zone
- Prevents "whipsaw" signals in choppy markets

**Implementation**: `engine/regime_buffer.py` → `detect_regime_with_hysteresis()`

### 8. Liquidity Check (Z-Score Based)

**Problem**: Low volume periods can cause poor execution quality.

**Solution**:
- Checks current volume vs 20-day average
- Delays entry if volume is 2+ standard deviations below mean
- 30-minute retry window with `retry_after` timestamp
- Prevents trading in illiquid conditions

### 9. Numerical Stability

**Problem**: Floating-point precision errors can cause "ghost" signals after 1000+ days.

**Solution**:
- All indicators rounded to 6 decimal places
- Epsilon-based comparisons (`EPSILON = 1e-6`) for trend crossings
- Zero-division guards in z-score calculations
- Precision-aware moving averages and volatility calculations

### 10. Enhanced API Resilience

**Problem**: API failures (429 rate limits, 5xx server errors) can disrupt trading.

**Solution**:
- Specific error handling for 429 (rate limit), 5xx (server errors), 401/403 (auth)
- Exponential backoff with `Retry-After` header support
- Circuit breaker integration (Guardian module)
- Graceful degradation to cached data when APIs unavailable

### 11. State Persistence & Crash Recovery

**Problem**: Bot crashes can lose position state or cause double-execution.

**Solution**:
- Atomic file writes (temp file + rename)
- File locking (`fcntl`) for thread safety
- Position state persisted to `data/state/positions.json`
- Trading state lock file prevents duplicate orders
- Automatic stale lock cleanup on startup

### 12. System Health Monitoring

**Problem**: Need visibility into system resources and API connectivity.

**Solution**:
- CPU, memory, disk usage tracking (via `psutil`)
- API health checks (Polygon, Alpaca connectivity)
- Integrated into heartbeat telemetry
- Watchdog timer restarts process if loop stalls >10 minutes

---

## Quick Start

### Prerequisites

- **Python 3.12+** (recommended: 3.12.0)
- **Alpaca Markets Account** ([Sign up](https://alpaca.markets/))
- **Polygon.io Account** (optional, for enhanced data quality)
- **Telegram Bot** (optional, for notifications)

### Installation

```bash
# Clone repository
git clone https://github.com/Reime-Flex/RegimeFlex.git
cd RegimeFlex

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuration

1. **Copy environment template**:
   ```bash
   cp env.example .env
   ```

2. **Edit `.env`** with your API keys:
   ```bash
   # Alpaca Markets (Paper Trading)
   ALPACA_KEY=your_paper_key_here
   ALPACA_SECRET=your_paper_secret_here
   
   # Polygon.io (Optional)
   POLYGON_KEY=your_polygon_key_here
   
   # Telegram (Optional)
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   
   # Environment
   ENV=dev  # Use 'prod' for live trading
   ```

3. **Review configuration files** in `regimeflex/config/`:
   - `risk.yaml` - Risk management parameters
   - `exposure.yaml` - Position sizing rules
   - `schedule.yaml` - Trading windows & guards
   - `telemetry.yaml` - Notification settings

### First Run

```bash
# Test run (dry-run mode, no real orders)
python -m regimeflex.scripts.run_offline_from_config

# Preview orders before execution
python -m regimeflex.scripts.plan_preview

# Check next scheduled run time
python -m regimeflex.scripts.next_run

# Reconcile positions (broker vs local)
python -m regimeflex.scripts.reconcile_positions
```

---

## Monitoring & Alerts

### Guardian Module

The **Guardian** module provides comprehensive process monitoring and automated recovery:

#### Watchdog Timer

- **Heartbeat File**: `.guardian_heartbeat` updated after each trading cycle
- **Staleness Detection**: If heartbeat age > 10 minutes, triggers recovery
- **Recovery Actions**: PM2 restart or process kill (configurable)
- **Health Status**: Tracks cycle count, last regime, equity, PID

#### System Health Monitoring

- **Resource Tracking**: CPU, memory, disk usage (via `psutil`)
- **API Connectivity**: Polygon and Alpaca API health checks
- **Heartbeat Integration**: Health metrics included in Telegram/Discord alerts

#### Alert Channels

1. **Telegram Bot**:
   - Daily heartbeat (every 4 hours)
   - Trade execution summaries
   - Risk alerts (kill switch, circuit breakers)
   - System health warnings

2. **Discord Webhook** (Optional):
   - Emergency alerts (API failures, watchdog triggers)
   - Critical error notifications

3. **SMS via Twilio** (Optional):
   - Emergency phone alerts for critical failures

### Monitoring Endpoints

```bash
# Health check endpoint (if health server enabled)
curl http://localhost:8080/health

# Status endpoint (read-only)
curl http://localhost:8080/status?token=YOUR_TOKEN

# Latest replay pack
curl http://localhost:8080/replay/latest?token=YOUR_TOKEN

# Recent incidents
curl http://localhost:8080/incidents?token=YOUR_TOKEN&limit=20
```

---

## Project Structure

```
RegimeFlex/
├── regimeflex/
│   ├── engine/              # Core trading engine (70+ modules)
│   │   ├── signals.py       # Regime detection & signal generation
│   │   ├── portfolio.py     # Target exposure computation
│   │   ├── risk.py          # Risk management & position sizing
│   │   ├── exec_alpaca.py   # Broker integration
│   │   ├── safety_wrapper.py # Slippage protection & duplicate prevention
│   │   ├── guardian/        # Process monitoring & alerts
│   │   │   ├── watchdog.py  # Heartbeat & staleness detection
│   │   │   ├── circuit_breaker.py # API failure protection
│   │   │   └── system_health.py # Resource monitoring
│   │   └── runner.py        # Daily cycle orchestrator
│   ├── config/              # YAML configuration files
│   ├── scripts/             # CLI tools & utilities (60+ scripts)
│   ├── docs/                # Comprehensive documentation
│   └── tests/               # Unit tests
├── data/                    # Local state & cache (gitignored)
├── logs/                    # Audit logs & incidents (gitignored)
├── reports/                 # Generated HTML reports (gitignored)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## Documentation

Comprehensive documentation is available in `regimeflex/docs/`:

- **[ARCHITECTURE.md](regimeflex/docs/ARCHITECTURE.md)** - System design and component overview
- **[DEPLOYMENT.md](regimeflex/docs/DEPLOYMENT.md)** - Production deployment guide
- **[EXECUTIONER.md](regimeflex/docs/EXECUTIONER.md)** - Execution safeguards and order management
- **[GUARDIAN.md](regimeflex/docs/GUARDIAN.md)** - Process monitoring and alerting
- **[PREFLIGHT_AUDIT.md](regimeflex/docs/PREFLIGHT_AUDIT.md)** - Security and risk audit report
- **[SAFETY_WRAPPER.md](regimeflex/docs/SAFETY_WRAPPER.md)** - Safety features deep dive

---

## Risk Disclaimer

**⚠️ CRITICAL: Trading involves substantial risk of loss.**

- This software is provided "as-is" without warranty of any kind
- Past performance does not guarantee future results
- Always test thoroughly in paper trading before live deployment
- Never trade with capital you cannot afford to lose
- Use proper risk management and position sizing
- Monitor your positions regularly
- Leveraged ETFs (TQQQ/SQQQ) amplify both gains and losses

**The authors, contributors, and maintainers are not responsible for any trading losses, financial damages, or other consequences resulting from the use of this software.**

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support

For questions, issues, or feature requests:

- **GitHub Issues**: [Create an issue](https://github.com/Reime-Flex/RegimeFlex/issues)
- **Documentation**: See `regimeflex/docs/` for detailed guides

---

**Built for systematic traders who value safety, transparency, and disciplined risk management.**
