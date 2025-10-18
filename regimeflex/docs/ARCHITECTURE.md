# RegimeFlex Architecture Documentation

## System Architecture Overview

RegimeFlex implements a modular, event-driven architecture designed for systematic trading with real broker integration. The system follows a clear separation of concerns with distinct layers for data, signals, risk, execution, and reporting.

## Core Architecture Principles

### 1. Modular Design
- **Single Responsibility**: Each module has a clear, focused purpose
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functionality grouped together

### 2. Configuration-Driven
- **YAML Configuration**: All settings externalized to configuration files
- **Environment Variables**: Sensitive data managed through environment variables
- **Runtime Flexibility**: System behavior controlled through configuration

### 3. Safety-First Design
- **Fail-Safe Defaults**: Safe defaults for all operations
- **Kill-Switch Protection**: Emergency stop capability
- **Dry-Run Mode**: Testing without real execution
- **Circuit Breakers**: Multiple layers of risk protection

## System Layers

### Data Layer
```
engine/data.py              # Data management and caching
engine/data_providers.py    # Live data providers
config/data.yaml           # Data provider configuration
data/cache/                # CSV data cache
```

**Responsibilities**:
- Market data ingestion and caching
- Data validation and quality checks
- Provider abstraction (cache, Polygon, Alpaca)
- Data normalization and formatting

### Signal Layer
```
engine/indicators.py        # Technical indicators
engine/signals.py          # Regime detection and signals
config/strategies.yaml     # Strategy parameters
```

**Responsibilities**:
- Technical indicator calculations
- Regime detection (bull/bear markets)
- Trading signal generation
- Strategy parameter management

### Risk Layer
```
engine/risk.py             # Risk management
engine/portfolio.py        # Portfolio management
config/risk.yaml          # Risk configuration
```

**Responsibilities**:
- Position sizing calculations
- Risk budget management
- Circuit breaker implementation
- Regime-based risk adjustment

### Execution Layer
```
engine/exec_planner.py     # Order planning
engine/exec_alpaca.py      # Broker integration
engine/reconcile.py        # Order reconciliation
config/broker.yaml         # Broker configuration
```

**Responsibilities**:
- Order planning and optimization
- Broker integration and communication
- Order execution and tracking
- Intent vs execution reconciliation

### Storage Layer
```
engine/storage.py          # Audit ledger
engine/positions.py        # Position management
engine/fills.py           # Fill processing
logs/audit/               # Audit trail
```

**Responsibilities**:
- ENS-style audit ledger
- Position tracking and updates
- Fill processing and application
- Transaction history management

### Orchestration Layer
```
engine/runner.py           # Daily cycle orchestrator
engine/calendar.py         # Calendar guard
engine/telemetry.py        # Notifications
engine/report.py          # Report generation
```

**Responsibilities**:
- Daily cycle coordination
- Calendar and timing management
- Notification and alerting
- Report generation and delivery

## Data Flow Architecture

### 1. Data Ingestion Flow
```
External APIs → Data Providers → Validation → Cache → Normalization
```

1. **Data Providers**: Polygon, Alpaca, or cache
2. **Validation**: Quality checks and format validation
3. **Caching**: Local CSV storage for performance
4. **Normalization**: Consistent format across providers

### 2. Signal Generation Flow
```
Market Data → Indicators → Regime Detection → Signal Generation
```

1. **Market Data**: OHLCV data from data layer
2. **Indicators**: Technical analysis calculations
3. **Regime Detection**: Bull/bear market identification
4. **Signal Generation**: Trading signals based on regime

### 3. Risk Management Flow
```
Signals → Risk Assessment → Position Sizing → Circuit Breakers
```

1. **Signals**: Trading signals from signal layer
2. **Risk Assessment**: Current risk and exposure analysis
3. **Position Sizing**: Dynamic position size calculation
4. **Circuit Breakers**: Risk-based trading blocks

### 4. Execution Flow
```
Risk-Adjusted Signals → Order Planning → Broker Integration → Execution
```

1. **Risk-Adjusted Signals**: Signals modified by risk layer
2. **Order Planning**: Order intent generation
3. **Broker Integration**: Real broker communication
4. **Execution**: Order placement and tracking

### 5. Storage and Reporting Flow
```
Execution Results → Audit Logging → Position Updates → Reporting
```

1. **Execution Results**: Order and fill information
2. **Audit Logging**: ENS-style transaction logging
3. **Position Updates**: Portfolio state updates
4. **Reporting**: HTML reports and notifications

## Component Interactions

### Core Engine Components

#### `engine/identity.py`
- **Purpose**: RegimeFlex branding and logging
- **Dependencies**: None
- **Used By**: All modules
- **Key Functions**: `print_log()`, branding constants

#### `engine/config.py`
- **Purpose**: YAML configuration management
- **Dependencies**: `pyyaml`
- **Used By**: All modules
- **Key Functions**: `Config` class, YAML loading

#### `engine/data.py`
- **Purpose**: Data management and caching
- **Dependencies**: `pandas`, `engine/data_providers.py`
- **Used By**: `engine/runner.py`, `engine/backtest.py`
- **Key Functions**: `get_daily_bars()`, `save_to_cache()`, `load_from_cache()`

#### `engine/signals.py`
- **Purpose**: Regime detection and signal generation
- **Dependencies**: `engine/indicators.py`, `engine/data.py`
- **Used By**: `engine/portfolio.py`, `engine/runner.py`
- **Key Functions**: `detect_regime()`, `trend_signal()`, `mr_signal()`

#### `engine/risk.py`
- **Purpose**: Risk management and circuit breakers
- **Dependencies**: `engine/indicators.py`, `engine/calendar.py`
- **Used By**: `engine/portfolio.py`, `engine/runner.py`
- **Key Functions**: `compute_position_size()`, `check_circuit_breakers()`

#### `engine/portfolio.py`
- **Purpose**: Target exposure computation
- **Dependencies**: `engine/signals.py`, `engine/risk.py`
- **Used By**: `engine/runner.py`, `engine/exec_planner.py`
- **Key Functions**: `compute_target_exposure()`

#### `engine/exec_planner.py`
- **Purpose**: Order planning and optimization
- **Dependencies**: `engine/portfolio.py`, `engine/positions.py`
- **Used By**: `engine/runner.py`, `engine/exec_alpaca.py`
- **Key Functions**: `plan_orders()`

#### `engine/exec_alpaca.py`
- **Purpose**: Alpaca broker integration
- **Dependencies**: `engine/exec_planner.py`, `requests`
- **Used By**: `engine/runner.py`, `scripts/broker_place_preview.py`
- **Key Functions**: `AlpacaExecutor.place_orders()`

#### `engine/runner.py`
- **Purpose**: Daily cycle orchestrator
- **Dependencies**: All engine modules
- **Used By**: `scripts/run_offline_from_config.py`
- **Key Functions**: `run_daily_offline()`

## Configuration Architecture

### Configuration Hierarchy
```
Environment Variables (.env)
    ↓
YAML Configuration Files (config/*.yaml)
    ↓
Runtime Configuration Objects
    ↓
Module-Specific Settings
```

### Configuration Files

#### `config/strategies.yaml`
- **Purpose**: Strategy parameters and settings
- **Used By**: `engine/signals.py`, `engine/backtest.py`
- **Key Settings**: SMA periods, Z-score thresholds, time stops

#### `config/risk.yaml`
- **Purpose**: Risk management configuration
- **Used By**: `engine/risk.py`, `engine/portfolio.py`
- **Key Settings**: Position sizing, circuit breakers, risk budgets

#### `config/broker.yaml`
- **Purpose**: Broker integration settings
- **Used By**: `engine/exec_alpaca.py`, `engine/runner.py`
- **Key Settings**: Broker mode, dry-run, API endpoints

#### `config/data.yaml`
- **Purpose**: Data provider configuration
- **Used By**: `engine/data.py`, `engine/data_providers.py`
- **Key Settings**: Provider selection, symbols, lookback periods

#### `config/run.yaml`
- **Purpose**: Run parameters and report settings
- **Used By**: `engine/runner.py`, `engine/report.py`
- **Key Settings**: Equity, VIX, timing, report configuration

## Safety Architecture

### Multi-Layer Safety System

#### 1. Kill-Switch Layer
```
config/kill_switch.flag → engine/killswitch.py → engine/runner.py
```
- **File-based Control**: Simple file existence check
- **Early Detection**: First check in runner execution
- **Hard Stop**: Immediate system shutdown
- **No Side Effects**: Clean abort without partial operations

#### 2. Broker Safety Layer
```
config/broker.yaml → engine/exec_alpaca.py → Dry-run mode
```
- **Dry-Run Default**: No live orders without explicit configuration
- **Paper Trading**: Safe testing environment
- **Config-Driven**: YAML-based broker control
- **Error Handling**: Comprehensive API error management

#### 3. Risk Safety Layer
```
config/risk.yaml → engine/risk.py → Circuit breakers
```
- **Position Limits**: Maximum position sizing
- **Circuit Breakers**: Multiple risk-based blocks
- **Regime Adaptation**: Risk scaling based on market conditions
- **Calendar Guard**: FOMC and OPEX protection

#### 4. Data Safety Layer
```
config/data.yaml → engine/data.py → Validation pipeline
```
- **Data Validation**: Quality checks and format validation
- **Cache Fallback**: Graceful fallback to cached data
- **Provider Isolation**: Error isolation between providers
- **Format Consistency**: Normalized data across providers

## Performance Architecture

### Caching Strategy
```
Live Data → Validation → Cache → Normalization → Application
```

1. **Cache-First**: Always try cache first unless forced refresh
2. **Live Fallback**: Fetch live data when cache unavailable
3. **Validation**: All data validated before caching
4. **Normalization**: Consistent format across providers

### Memory Management
- **Lazy Loading**: Configuration loaded on demand
- **Data Streaming**: Large datasets processed in chunks
- **Cache Limits**: Automatic cache cleanup and rotation
- **Resource Monitoring**: Memory usage tracking and optimization

### Concurrency Model
- **Single-Threaded**: Sequential processing for consistency
- **Event-Driven**: Asynchronous notification handling
- **State Management**: Immutable state objects
- **Transaction Safety**: Atomic operations for critical sections

## Extensibility Architecture

### Plugin System
```
Core Engine → Plugin Interface → Custom Modules
```

1. **Interface Definition**: Well-defined interfaces for extensions
2. **Configuration Integration**: Plugin settings in YAML
3. **Dependency Injection**: Runtime module loading
4. **Error Isolation**: Plugin failures don't crash system

### Custom Strategies
```
engine/signals.py → Strategy Interface → Custom Strategies
```

1. **Strategy Interface**: Standard interface for custom strategies
2. **Parameter Management**: YAML-based parameter configuration
3. **Backtesting Integration**: Custom strategies in backtesting
4. **Performance Tracking**: Strategy-specific performance metrics

### Custom Data Providers
```
engine/data_providers.py → Provider Interface → Custom Providers
```

1. **Provider Interface**: Standard interface for data providers
2. **Format Normalization**: Consistent data format across providers
3. **Error Handling**: Graceful provider failure management
4. **Caching Integration**: Provider-specific caching strategies

## Monitoring Architecture

### Audit Trail System
```
engine/storage.py → ENS-Style Ledger → logs/audit/
```

1. **Append-Only**: Immutable transaction history
2. **Deterministic Hashing**: SHA256-based transaction IDs
3. **Timestamping**: RFC3339 timestamps for all entries
4. **Block Structure**: Daily "block height" organization

### Logging System
```
engine/identity.py → Colorized Logging → Console Output
```

1. **Branded Logging**: RegimeFlex visual identity
2. **Color Coding**: INFO, SUCCESS, RISK, ERROR levels
3. **Structured Output**: Consistent log format
4. **Performance Tracking**: Execution time and resource usage

### Notification System
```
engine/telemetry.py → Telegram Integration → Real-time Alerts
```

1. **Config-Driven**: YAML-based notification settings
2. **Multiple Channels**: Telegram, email, webhook support
3. **Alert Levels**: Different notification types and priorities
4. **Rate Limiting**: Prevent notification spam

## Security Architecture

### API Key Management
```
.env → engine/env.py → Secure Loading
```

1. **Environment Variables**: Sensitive data in environment
2. **Secure Loading**: Safe credential management
3. **Key Rotation**: Support for key updates
4. **Access Control**: Principle of least privilege

### Data Security
```
Data Providers → Validation → Encryption → Storage
```

1. **Data Validation**: Input sanitization and validation
2. **Format Security**: Safe data format handling
3. **Storage Security**: Encrypted sensitive data storage
4. **Transmission Security**: HTTPS for all API calls

### Operational Security
```
Kill-Switch → Circuit Breakers → Error Handling → Recovery
```

1. **Emergency Controls**: Kill-switch for immediate shutdown
2. **Circuit Breakers**: Automatic risk-based blocks
3. **Error Handling**: Graceful failure management
4. **Recovery Procedures**: Automated recovery and restart

---

**RegimeFlex Architecture v29** - Modular, event-driven architecture designed for systematic trading with comprehensive safety, performance, and extensibility features.

*Engineered for reliability, designed for scalability, built for performance.*
