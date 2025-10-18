# Changelog

All notable changes to the RegimeFlex Trading System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [29.0.0] - 2024-10-18

### Added
- **Step 29**: File-based kill-switch system for emergency trading halt
  - `config/kill_switch.flag` file for simple on/off control
  - `engine/killswitch.py` utility module with enable/disable functions
  - Early kill-switch detection in `engine/runner.py` before any trading actions
  - `scripts/kill_switch.py` for easy toggling of kill-switch state
  - Hard stop protection with no side effects when kill-switch is active
  - Safe abort mechanism with structured response and kill-switch indicator

### Changed
- Enhanced runner safety with kill-switch integration
- Improved emergency control capabilities
- Added kill-switch status to breadcrumbs in daily reports

### Security
- Added file-based emergency stop system
- Enhanced operational safety with kill-switch protection
- Improved system shutdown capabilities

## [28.0.0] - 2024-10-18

### Added
- **Step 28**: Optional real broker integration in daily run with reconciliation
  - Enhanced `config/broker.yaml` with `enabled` flag for broker integration
  - `engine/reconcile.py` with `compare_intents_vs_orders` function for order reconciliation
  - Integrated broker placement into `engine/runner.py` with config-driven control
  - Order reconciliation comparing planned intents vs broker responses
  - Enhanced audit logging for both dry-run payloads and live API responses
  - Comprehensive broker integration testing with various configuration scenarios

### Changed
- Modified `engine/runner.py` to include optional broker placement
- Enhanced audit logging to differentiate between dry-run and live orders
- Improved broker integration with config-driven control

### Security
- Maintained dry-run default for broker operations
- Added comprehensive error handling for broker API calls
- Enhanced order reconciliation for audit trail integrity

## [27.0.0] - 2024-10-18

### Added
- **Step 27**: Real Alpaca order placement with paper trading and dry-run safety
  - Enhanced `engine/exec_alpaca.py` with real HTTP requests for order placement
  - `ALPACA_PAPER_URL` and `ALPACA_LIVE_URL` constants for environment selection
  - `AlpacaCreds` class with `base_url` parameter for paper/live switching
  - `_headers()` method for API authentication
  - Complete rewrite of `place_orders()` method with real API integration
  - `config/broker.yaml` configuration file for broker settings
  - `scripts/broker_place_preview.py` for testing order placement
  - Enhanced audit logging for both dry-run payloads and live API responses
  - MOC order handling with `market` type and `cls` time-in-force

### Changed
- Modified `engine/exec_alpaca.py` to support real API calls
- Enhanced order placement with comprehensive error handling
- Improved broker integration with config-driven control

### Security
- Implemented dry-run mode as default safety mechanism
- Added comprehensive API error handling
- Enhanced credential management with environment variables

## [26.0.0] - 2024-10-18

### Added
- **Step 26**: Real data ingestion with config-switchable providers
  - `config/data.yaml` configuration file for data provider settings
  - `engine/data_providers.py` with Polygon and Alpaca data providers
  - `fetch_polygon_daily()` function for Polygon.io data integration
  - `fetch_alpaca_daily()` function for Alpaca Markets data integration
  - Enhanced `engine/data.py` with `get_daily_bars_with_provider()` function
  - `scripts/fetch_live_to_cache.py` for data ingestion and cache updates
  - Provider-specific configuration with base URLs and parameters
  - Graceful fallback to cache when live data providers fail
  - Comprehensive error handling for API calls and data validation

### Changed
- Modified `engine/data.py` to support multiple data providers
- Enhanced data caching with provider-specific handling
- Improved data validation with provider-specific error handling

### Fixed
- Fixed f-string syntax error with `from` keyword in URL formatting
- Fixed pandas datetime normalization method call
- Enhanced error handling for API failures with graceful fallback

## [25.0.0] - 2024-10-18

### Added
- **Step 25**: Config-driven offline run with HTML report generation
  - `config/run.yaml` configuration file for run parameters and report settings
  - `engine/report.py` with `write_daily_html()` function for HTML report generation
  - `scripts/run_offline_from_config.py` for config-driven daily runs
  - Enhanced `engine/config.py` with `run` property for run configuration
  - HTML report generation with RegimeFlex branding and styling
  - Configurable report settings including output directory and filename prefix
  - Integration with existing telemetry system for notifications

### Changed
- Modified `engine/config.py` to include run configuration
- Enhanced daily run with config-driven parameters
- Improved report generation with HTML output

### Features
- Added comprehensive HTML report generation
- Enhanced configuration management for run parameters
- Improved daily run orchestration with config-driven control

## [24.0.0] - 2024-10-18

### Added
- **Step 24**: CSV export and visualization plots for parameter sweep
  - Enhanced `scripts/sweep_preview.py` with CSV export functionality
  - `save_csv()` function for exporting sweep results to CSV
  - `plot_scatter()` function for MAR vs Sharpe scatter plots
  - `plot_pivot()` function for parameter sensitivity heatmaps
  - `reports/` directory for storing generated reports and visualizations
  - Matplotlib integration for data visualization
  - Comprehensive parameter sweep results with performance metrics

### Changed
- Modified `scripts/sweep_preview.py` to include visualization capabilities
- Enhanced parameter sweep with export and plotting functionality
- Improved results analysis with visual representations

### Features
- Added CSV export for parameter sweep results
- Enhanced visualization with scatter plots and heatmaps
- Improved parameter optimization workflow

## [23.0.0] - 2024-10-18

### Added
- **Step 23**: Parameter sweep hooks and grid runner
  - Enhanced `engine/backtest.py` with parameter passing capabilities
  - Modified `engine/signals.py` with parameterized `mr_signal()` function
  - `scripts/sweep_preview.py` for parameter optimization
  - `scripts/test_parameter_hooks.py` for testing parameter integration
  - Grid search functionality for strategy parameter optimization
  - Performance ranking and comparison of parameter combinations
  - Comprehensive parameter sweep framework

### Changed
- Modified `engine/backtest.py` to accept strategy parameters
- Enhanced `engine/signals.py` with parameterized signal functions
- Improved backtesting framework with parameter optimization

### Features
- Added parameter sweep capabilities
- Enhanced strategy optimization workflow
- Improved backtesting with parameter hooks

## [22.0.0] - 2024-10-18

### Added
- **Step 22**: Transaction costs and slippage to backtester
  - Enhanced `engine/backtest.py` with friction modeling
  - `_slip()` helper function for slippage calculation
  - Extended `BTConfig` with friction parameters
  - `scripts/test_friction_effects.py` for testing friction impact
  - Commission per share, fixed fees, and basis-point slippage modeling
  - Realistic trading cost simulation in backtesting

### Changed
- Modified `engine/backtest.py` to include transaction costs
- Enhanced backtesting with realistic friction modeling
- Improved performance metrics with cost-adjusted returns

### Features
- Added transaction cost modeling
- Enhanced slippage simulation
- Improved backtesting realism

## [21.0.0] - 2024-10-18

### Added
- **Step 21**: Backtest scaffold with core metrics
  - `engine/backtest.py` with comprehensive backtesting framework
  - `scripts/backtest_preview.py` for backtesting demonstration
  - Core performance metrics: CAGR, Max Drawdown, Sharpe Ratio
  - Equity curve tracking and trade statistics
  - Historical data processing with cache-only data
  - Performance analysis and reporting

### Changed
- Enhanced backtesting capabilities
- Improved performance metrics calculation
- Added comprehensive trade analysis

### Fixed
- Fixed `IndexError` with empty equity series in `_metrics()`
- Fixed warmup calculation for short datasets
- Enhanced error handling for edge cases

### Features
- Added comprehensive backtesting framework
- Enhanced performance metrics calculation
- Improved historical data analysis

## [20.0.0] - 2024-10-18

### Added
- **Step 20**: Config-gated notifications with enriched breadcrumbs
  - Enhanced `config/telemetry.yaml` with verbosity control
  - Modified `engine/telemetry.py` with `format_run_summary()` function
  - Enhanced breadcrumbs with VIX assumption, FOMC blackout, and OPEX status
  - Config-driven notification control with verbosity levels
  - Improved notification formatting and content

### Changed
- Modified `engine/telemetry.py` to support config-driven notifications
- Enhanced notification content with enriched breadcrumbs
- Improved notification formatting and control

### Features
- Added config-driven notification control
- Enhanced notification content with breadcrumbs
- Improved notification verbosity and formatting

## [19.0.0] - 2024-10-18

### Added
- **Step 19**: Minimal Telegram notifier with branded messaging
  - `engine/telemetry.py` with Telegram notification system
  - `TGCreds` dataclass for Telegram credentials
  - `Notifier` class with `send()` method for message delivery
  - `format_run_summary()` function for run result formatting
  - `config/telemetry.yaml` configuration file for notification settings
  - Branded messaging with RegimeFlex identity
  - Dry-run fallback for notification testing

### Changed
- Enhanced notification system with Telegram integration
- Improved messaging with RegimeFlex branding
- Added comprehensive notification configuration

### Features
- Added Telegram notification system
- Enhanced messaging with branding
- Improved notification configuration and control

## [18.0.0] - 2024-10-18

### Added
- **Step 18**: Calendar guard integration with risk management
  - `engine/calendar.py` with FOMC and OPEX detection
  - `is_fomc_blackout()` function for FOMC meeting detection
  - `is_opex()` function for OPEX day detection
  - `config/schedule.yaml` configuration file for calendar settings
  - Enhanced `engine/risk.py` with calendar guard integration
  - `RiskInputs` dataclass with calendar booleans
  - Comprehensive calendar-based risk management

### Changed
- Modified `engine/risk.py` to include calendar guard
- Enhanced risk management with calendar-based controls
- Improved risk assessment with calendar integration

### Features
- Added calendar guard system
- Enhanced risk management with calendar controls
- Improved risk assessment with calendar integration

## [17.0.0] - 2024-10-18

### Added
- **Step 17**: ENS-style audit ledger with deterministic hashing
  - `engine/storage.py` with `ENSStyleAudit` class
  - `log()` method for transaction logging
  - RFC3339 timestamps and deterministic SHA256 hashes
  - Daily "block height" organization
  - `logs/audit/` directory for audit trail storage
  - Comprehensive transaction logging system

### Changed
- Enhanced audit system with ENS-style ledger
- Improved transaction logging with deterministic hashing
- Added comprehensive audit trail management

### Features
- Added ENS-style audit ledger
- Enhanced transaction logging with deterministic hashing
- Improved audit trail management and organization

## [16.0.0] - 2024-10-18

### Added
- **Step 16**: Fill simulation and position management
  - `engine/fills.py` with fill simulation and processing
  - `simulate_fills()` function for order fill simulation
  - `apply_simulated_fills()` function for position updates
  - Enhanced `engine/positions.py` with fill application logic
  - Comprehensive fill processing and position management

### Changed
- Modified `engine/positions.py` to include fill processing
- Enhanced position management with fill simulation
- Improved position tracking and updates

### Features
- Added fill simulation system
- Enhanced position management with fill processing
- Improved position tracking and updates

## [15.0.0] - 2024-10-18

### Added
- **Step 15**: Position management and storage
  - `engine/positions.py` with position management
  - `load_positions()` and `save_positions()` functions
  - JSON-based position storage with atomic writes
  - Broker-agnostic position management
  - Comprehensive position tracking and updates

### Changed
- Enhanced position management with JSON storage
- Improved position tracking with atomic writes
- Added broker-agnostic position management

### Features
- Added position management system
- Enhanced position tracking with JSON storage
- Improved position management with atomic writes

## [14.0.0] - 2024-10-18

### Added
- **Step 14**: Order planning and execution logic
  - `engine/exec_planner.py` with order planning
  - `plan_orders()` function for order intent generation
  - `OrderIntent` dataclass for order representation
  - MOC vs limit/market order handling
  - Minimum trade value enforcement
  - Comprehensive order planning and optimization

### Changed
- Enhanced order planning with intent generation
- Improved order execution with comprehensive logic
- Added order optimization and planning

### Features
- Added order planning system
- Enhanced order execution with comprehensive logic
- Improved order optimization and planning

## [13.0.0] - 2024-10-18

### Added
- **Step 13**: Portfolio orchestration and target exposure
  - `engine/portfolio.py` with portfolio management
  - `compute_target_exposure()` function for target calculation
  - `TargetExposure` dataclass for target representation
  - Regime-based portfolio management
  - Comprehensive portfolio orchestration

### Changed
- Enhanced portfolio management with target exposure
- Improved portfolio orchestration with regime-based logic
- Added comprehensive portfolio management

### Features
- Added portfolio orchestration system
- Enhanced portfolio management with target exposure
- Improved portfolio orchestration with regime-based logic

## [12.0.0] - 2024-10-18

### Added
- **Step 12**: Risk management and circuit breakers
  - `engine/risk.py` with comprehensive risk management
  - `RiskConfig` dataclass for risk configuration
  - `compute_position_size()` function for position sizing
  - `check_circuit_breakers()` function for risk controls
  - VIX-based volatility blocks and realized volatility limits
  - Dynamic position sizing with ATR-based calculations

### Changed
- Enhanced risk management with circuit breakers
- Improved position sizing with dynamic calculations
- Added comprehensive risk controls

### Features
- Added risk management system
- Enhanced risk controls with circuit breakers
- Improved position sizing with dynamic calculations

## [11.0.0] - 2024-10-18

### Added
- **Step 11**: Trading signals and regime detection
  - `engine/signals.py` with signal generation
  - `detect_regime()` function for regime detection
  - `trend_signal()` function for trend following
  - `mr_signal()` function for mean reversion
  - `RegimeState`, `TrendSignal`, and `MRSignal` dataclasses
  - Comprehensive signal generation and regime detection

### Changed
- Enhanced signal generation with regime detection
- Improved trading signals with comprehensive logic
- Added regime-based signal generation

### Features
- Added trading signal system
- Enhanced regime detection with comprehensive logic
- Improved signal generation with regime-based logic

## [10.0.0] - 2024-10-18

### Added
- **Step 10**: Technical indicators and analysis
  - `engine/indicators.py` with technical indicators
  - SMA, EMA, ATR, rolling standard deviation, realized volatility
  - Z-score calculation and comparison helpers
  - Comprehensive technical analysis capabilities

### Changed
- Enhanced technical analysis with comprehensive indicators
- Improved technical analysis with advanced calculations
- Added comprehensive technical analysis framework

### Features
- Added technical indicator system
- Enhanced technical analysis with comprehensive indicators
- Improved technical analysis with advanced calculations

## [9.0.0] - 2024-10-18

### Added
- **Step 9**: Data validation and quality checks
  - Enhanced `engine/data.py` with data validation
  - `run_validations()` function for data quality checks
  - Non-empty check, column validation, sorting check
  - Recency check and volume validation
  - Comprehensive data quality assurance

### Changed
- Enhanced data validation with comprehensive checks
- Improved data quality with validation pipeline
- Added comprehensive data quality assurance

### Features
- Added data validation system
- Enhanced data quality with comprehensive checks
- Improved data quality with validation pipeline

## [8.0.0] - 2024-10-18

### Added
- **Step 8**: Data caching and storage
  - Enhanced `engine/data.py` with caching capabilities
  - `save_to_cache()` and `load_from_cache()` functions
  - CSV-based data storage with intelligent caching
  - `data/cache/` directory for data storage
  - Comprehensive data caching and storage

### Changed
- Enhanced data management with caching
- Improved data storage with CSV-based caching
- Added comprehensive data caching system

### Features
- Added data caching system
- Enhanced data storage with CSV-based caching
- Improved data management with intelligent caching

## [7.0.0] - 2024-10-18

### Added
- **Step 7**: Market data management
  - `engine/data.py` with market data management
  - `get_daily_bars()` function for data access
  - OHLCV data handling and processing
  - Comprehensive market data management

### Changed
- Enhanced data management with market data
- Improved data handling with OHLCV processing
- Added comprehensive market data management

### Features
- Added market data management system
- Enhanced data handling with OHLCV processing
- Improved data management with market data

## [6.0.0] - 2024-10-18

### Added
- **Step 6**: Environment variable management
  - `engine/env.py` with environment management
  - `load_env()` function for environment loading
  - API key management and credential handling
  - Comprehensive environment variable management

### Changed
- Enhanced environment management with variable loading
- Improved credential management with API keys
- Added comprehensive environment variable management

### Features
- Added environment variable management
- Enhanced credential management with API keys
- Improved environment management with variable loading

## [5.0.0] - 2024-10-18

### Added
- **Step 5**: YAML configuration management
  - `engine/config.py` with configuration management
  - `Config` class for YAML configuration loading
  - `config/strategies.yaml` for strategy parameters
  - `config/risk.yaml` for risk management settings
  - `config/schedule.yaml` for calendar settings
  - `config/telemetry.yaml` for notification settings
  - Comprehensive configuration management

### Changed
- Enhanced configuration management with YAML
- Improved configuration loading with comprehensive settings
- Added comprehensive configuration management

### Features
- Added YAML configuration management
- Enhanced configuration loading with comprehensive settings
- Improved configuration management with YAML

## [4.0.0] - 2024-10-18

### Added
- **Step 4**: RegimeFlex branding and identity
  - `engine/identity.py` with RegimeFlex branding
  - `RegimeFlexIdentity` class with branding constants
  - `print_log()` function with colorized logging
  - RegimeFlex color palette and visual identity
  - Comprehensive branding and identity system

### Changed
- Enhanced branding with RegimeFlex identity
- Improved logging with colorized output
- Added comprehensive branding system

### Features
- Added RegimeFlex branding system
- Enhanced logging with colorized output
- Improved branding with comprehensive identity

## [3.0.0] - 2024-10-18

### Added
- **Step 3**: Project structure and organization
  - Complete project structure with organized directories
  - `engine/` directory for core trading engine
  - `config/` directory for configuration files
  - `scripts/` directory for execution scripts
  - `data/` directory for data storage
  - `logs/` directory for audit and logging
  - `reports/` directory for generated reports
  - `branding/` directory for design system assets

### Changed
- Enhanced project organization with structured directories
- Improved project structure with comprehensive organization
- Added comprehensive project organization

### Features
- Added project structure and organization
- Enhanced project organization with structured directories
- Improved project structure with comprehensive organization

## [2.0.0] - 2024-10-18

### Added
- **Step 2**: Python environment and dependencies
  - Python virtual environment setup
  - `requirements.txt` with core dependencies
  - Development environment configuration
  - Comprehensive Python environment setup

### Changed
- Enhanced Python environment with virtual environment
- Improved dependency management with requirements
- Added comprehensive Python environment setup

### Features
- Added Python environment setup
- Enhanced dependency management with requirements
- Improved Python environment with virtual environment

## [1.0.0] - 2024-10-18

### Added
- **Step 1**: Initial project setup
  - Initial project structure
  - Basic project configuration
  - Foundation for systematic trading system
  - Comprehensive project foundation

### Features
- Added initial project setup
- Enhanced project foundation with basic configuration
- Improved project structure with initial setup

---

**RegimeFlex Trading System v29** - Complete systematic trading stack with real broker integration, professional reporting, and comprehensive safety features.

*Built with precision, designed for trust, engineered for performance.*
