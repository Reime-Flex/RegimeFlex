# RegimeFlex Development Guide

## Development Environment Setup

### Prerequisites

- **Python**: 3.12+ (recommended: 3.12.0)
- **Git**: Version control
- **IDE**: VS Code, PyCharm, or similar
- **Terminal**: Bash, Zsh, or PowerShell

### Local Development Setup

```bash
# Clone repository
git clone <repository-url> regimeflex
cd regimeflex

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy
```

### Development Dependencies

```bash
# Testing
pip install pytest pytest-cov pytest-mock

# Code formatting
pip install black isort

# Linting
pip install flake8 mypy

# Documentation
pip install sphinx sphinx-rtd-theme
```

## Project Structure

```
regimeflex/
├── engine/                 # Core trading engine
│   ├── __init__.py
│   ├── identity.py         # RegimeFlex branding and logging
│   ├── config.py          # YAML configuration management
│   ├── env.py             # Environment variable handling
│   ├── data.py            # Market data with caching
│   ├── indicators.py      # Technical indicators
│   ├── signals.py         # Regime detection and signals
│   ├── risk.py            # Risk management
│   ├── portfolio.py       # Portfolio management
│   ├── exec_planner.py    # Order planning
│   ├── exec_alpaca.py     # Broker integration
│   ├── reconcile.py       # Order reconciliation
│   ├── positions.py       # Position management
│   ├── fills.py           # Fill processing
│   ├── storage.py         # Audit ledger
│   ├── calendar.py        # Calendar guard
│   ├── telemetry.py       # Notifications
│   ├── report.py          # Report generation
│   ├── killswitch.py      # Emergency controls
│   ├── data_providers.py  # Live data providers
│   ├── backtest.py        # Backtesting framework
│   └── runner.py          # Daily cycle orchestrator
├── config/                # Configuration files
│   ├── strategies.yaml    # Strategy parameters
│   ├── risk.yaml          # Risk management
│   ├── schedule.yaml      # Calendar settings
│   ├── telemetry.yaml     # Notification settings
│   ├── run.yaml           # Run parameters
│   ├── data.yaml          # Data provider settings
│   ├── broker.yaml        # Broker settings
│   └── kill_switch.flag   # Emergency kill-switch
├── scripts/               # Execution scripts
│   ├── run_offline_from_config.py
│   ├── broker_place_preview.py
│   ├── fetch_live_to_cache.py
│   ├── sweep_preview.py
│   ├── backtest_preview.py
│   └── kill_switch.py
├── data/                  # Data storage
│   └── cache/             # CSV data cache
├── logs/                  # Audit and logging
│   └── audit/             # ENS-style audit ledger
├── reports/               # Generated reports
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_engine/
│   ├── test_scripts/
│   └── test_integration/
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── .flake8               # Flake8 configuration
├── .mypy.ini             # MyPy configuration
├── pyproject.toml        # Project configuration
└── README.md             # Main documentation
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... edit files ...

# Test changes
python -m pytest tests/
python scripts/run_offline_from_config.py

# Commit changes
git add .
git commit -m "Add new feature: description"

# Push branch
git push origin feature/new-feature
```

### 2. Code Quality

```bash
# Format code
black engine/ scripts/ tests/
isort engine/ scripts/ tests/

# Lint code
flake8 engine/ scripts/ tests/
mypy engine/ scripts/ tests/

# Run tests
pytest tests/ -v --cov=engine
```

### 3. Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_engine/test_signals.py -v

# Run with coverage
pytest tests/ --cov=engine --cov-report=html

# Run integration tests
pytest tests/test_integration/ -v
```

## Code Standards

### Python Style Guide

```python
# Use type hints
def compute_position_size(
    price: float,
    atr: float,
    risk_budget: float = 0.02
) -> float:
    """Compute position size based on ATR and risk budget."""
    return (risk_budget * price) / atr

# Use dataclasses for data structures
@dataclass
class TargetExposure:
    symbol: str
    direction: str
    dollars: float
    shares: float
    notes: str

# Use descriptive variable names
current_positions = load_positions()
target_exposure = compute_target_exposure(data, equity)
order_intents = plan_orders(current_positions, target_exposure)
```

### Documentation Standards

```python
def detect_regime(price_data: pd.DataFrame) -> RegimeState:
    """
    Detect market regime based on technical indicators.
    
    Args:
        price_data: DataFrame with OHLCV data
        
    Returns:
        RegimeState: Bull/bear market state
        
    Raises:
        DataError: If price_data is invalid
    """
    # Implementation here
    pass
```

### Error Handling

```python
try:
    data = get_daily_bars(symbol)
except DataError as e:
    RF.print_log(f"Data error for {symbol}: {e}", "ERROR")
    raise
except Exception as e:
    RF.print_log(f"Unexpected error: {e}", "ERROR")
    raise
```

## Testing Framework

### Unit Tests

**File**: `tests/test_engine/test_signals.py`
```python
import pytest
import pandas as pd
from engine.signals import detect_regime, trend_signal
from engine.identity import RegimeFlexIdentity as RF

class TestSignals:
    def test_detect_regime_bull(self):
        # Create test data
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104]
        })
        
        # Test regime detection
        regime = detect_regime(data)
        assert regime.bull is True
        
    def test_trend_signal_long(self):
        # Create test data
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104]
        })
        
        # Test trend signal
        regime = detect_regime(data)
        signal = trend_signal(data, regime)
        assert signal.direction == "LONG"
```

### Integration Tests

**File**: `tests/test_integration/test_daily_cycle.py`
```python
import pytest
from engine.runner import run_daily_offline
from engine.identity import RegimeFlexIdentity as RF

class TestDailyCycle:
    def test_daily_cycle_offline(self):
        # Test offline daily cycle
        result = run_daily_offline(
            equity=25000.0,
            vix=20.0,
            minutes_to_close=30,
            min_trade_value=200.0
        )
        
        # Verify result structure
        assert "target" in result
        assert "positions_before" in result
        assert "intents" in result
        assert "positions_after" in result
        assert "breadcrumbs" in result
```

### Mock Tests

**File**: `tests/test_engine/test_exec_alpaca.py`
```python
import pytest
from unittest.mock import Mock, patch
from engine.exec_alpaca import AlpacaExecutor, AlpacaCreds

class TestAlpacaExecutor:
    @patch('requests.post')
    def test_place_orders_dry_run(self, mock_post):
        # Setup
        creds = AlpacaCreds(key="test", secret="test")
        executor = AlpacaExecutor(creds, dry_run=True)
        
        # Test dry-run mode
        intents = [Mock(symbol="QQQ", side="BUY", qty=10)]
        results = executor.place_orders(intents)
        
        # Verify no API calls in dry-run
        mock_post.assert_not_called()
        assert len(results) == 1
```

## Configuration Management

### Development Configuration

**File**: `config/strategies.yaml`
```yaml
# Development settings
trend:
  sma_fast: 5
  sma_slow: 20
  sma_trend: 50

mean_reversion:
  z_len: 20
  z_entry_bull: -2.0
  z_exit_bull: 0.0
```

### Environment Configuration

**File**: `.env.development`
```bash
# Development environment
ALPACA_KEY=dev_key
ALPACA_SECRET=dev_secret
POLYGON_KEY=dev_polygon_key
TELEGRAM_BOT_TOKEN=dev_bot_token
TELEGRAM_CHAT_ID=dev_chat_id
```

### Test Configuration

**File**: `config/test.yaml`
```yaml
# Test-specific settings
equity: 10000.0
vix_assumption: 15.0
minutes_to_close: 5
min_trade_value: 100.0
```

## Debugging and Profiling

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug output
python -u scripts/run_offline_from_config.py 2>&1 | tee debug.log
```

### Performance Profiling

```python
# Profile execution
python -m cProfile scripts/run_offline_from_config.py

# Memory profiling
python -m memory_profiler scripts/run_offline_from_config.py

# Line-by-line profiling
python -m line_profiler scripts/run_offline_from_config.py
```

### Debugging Tools

```python
# Interactive debugging
import pdb; pdb.set_trace()

# Logging debug information
from engine.identity import RegimeFlexIdentity as RF
RF.print_log(f"Debug: {variable}", "INFO")

# Exception handling
try:
    # Code here
    pass
except Exception as e:
    RF.print_log(f"Exception: {e}", "ERROR")
    import traceback
    traceback.print_exc()
```

## Continuous Integration

### GitHub Actions

**File**: `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 engine/ scripts/ tests/
    
    - name: Type check with mypy
      run: |
        mypy engine/ scripts/ tests/
    
    - name: Test with pytest
      run: |
        pytest tests/ -v --cov=engine
```

### Pre-commit Hooks

**File**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

## Release Management

### Version Control

```bash
# Create release branch
git checkout -b release/v1.0.0

# Update version
echo "1.0.0" > VERSION

# Commit release
git add VERSION
git commit -m "Release v1.0.0"

# Tag release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Release Notes

**File**: `CHANGELOG.md`
```markdown
# Changelog

## [1.0.0] - 2024-01-01

### Added
- Complete systematic trading system
- Real broker integration with Alpaca
- Comprehensive risk management
- Professional reporting and notifications
- Kill-switch emergency controls

### Changed
- Improved performance and reliability
- Enhanced error handling and logging

### Fixed
- Bug fixes and stability improvements
```

## Documentation

### API Documentation

```python
# Generate API documentation
sphinx-build -b html docs/ docs/_build/html

# Serve documentation locally
cd docs/_build/html
python -m http.server 8000
```

### Code Documentation

```python
# Use docstrings for all functions
def compute_position_size(price: float, atr: float) -> float:
    """
    Compute position size based on ATR.
    
    Args:
        price: Current price
        atr: Average True Range
        
    Returns:
        Position size in shares
    """
    return price / atr
```

## Performance Optimization

### Code Optimization

```python
# Use vectorized operations
df['sma_20'] = df['close'].rolling(20).mean()

# Avoid loops when possible
df['returns'] = df['close'].pct_change()

# Use efficient data structures
from collections import defaultdict
position_dict = defaultdict(float)
```

### Memory Optimization

```python
# Use appropriate data types
df['volume'] = df['volume'].astype('int32')
df['price'] = df['price'].astype('float32')

# Clean up large objects
del large_dataframe
import gc
gc.collect()
```

### Caching

```python
# Use functools.lru_cache for expensive computations
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(param: str) -> float:
    # Expensive computation here
    return result
```

## Security

### API Key Security

```python
# Never hardcode API keys
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ALPACA_KEY')
```

### Input Validation

```python
# Validate all inputs
def validate_symbol(symbol: str) -> str:
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Invalid symbol")
    return symbol.upper()
```

### Error Handling

```python
# Handle errors gracefully
try:
    result = risky_operation()
except SpecificError as e:
    RF.print_log(f"Specific error: {e}", "ERROR")
    return default_value
except Exception as e:
    RF.print_log(f"Unexpected error: {e}", "ERROR")
    raise
```

---

**RegimeFlex Development Guide v29** - Comprehensive development workflow with testing, quality assurance, and deployment procedures.

*Developed with precision, tested with rigor, deployed with confidence.*
