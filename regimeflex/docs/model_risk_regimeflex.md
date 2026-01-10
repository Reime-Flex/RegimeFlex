# RegimeFlex — Model Risk & System Description

## 1. Overview

**Name:** RegimeFlex  
**Type:** Fully systematic EOD long/short strategy on QQQ + inverse QQQ  
**Universe:** QQQ (long), PSQ or SQQQ-equivalent short leg (currently unleveraged)  
**Execution:** End-of-day (EOD), ~10 minutes before US cash close  
**Implementation:** Python + Alpaca + Telegram, daily cron schedule

RegimeFlex is a deterministic trading model that allocates between long QQQ, short QQQ (via inverse ETF), or cash based on trend, regime state, and mean-reversion signals, with a layered risk and execution control framework.

## 2. Strategy Logic (High-Level)

### 2.1 Inputs

- Daily OHLCV bars for:
  - QQQ (primary underlying)
  - Inverse QQQ leg (e.g., PSQ/SQQQ-equivalent)
- VIX index level and rolling volatility of the benchmark (e.g., QQQ / NDX)
- Internal state:
  - Current positions
  - Rolling indicators (moving averages, volatility, ADV)
  - Execution statistics (slippage, fills)

### 2.2 Signal Engines

1. **Trend Engine**
   - Uses moving averages (e.g., 20 / 50 / 200) and price vs SMA relationships
   - Determines whether the system should be net long, net short, or neutral
   - Also uses volatility regime filters (e.g., avoid very high VIX regimes)

2. **Mean-Reversion Engine**
   - Uses regime-aware z-score of price vs a mid-term moving average
   - In bull regimes: looks for oversold dips to add long risk
   - In bear regimes: looks for overbought bounces to add short risk
   - Holding period constraints (max days in MR leg)

### 2.3 Allocation & Positioning

- Converts regime + MR view into a **target exposure** (e.g., +100%, 0%, -100%).
- Applies:
  - Volatility-based position sizing (e.g., ATR / price)
  - Caps based on risk budget and max position % of portfolio
- Output is a desired dollar and share exposure per symbol.

### 2.4 Execution

- Once per day:
  - Compute target positions
  - Compare vs current broker positions
  - Generate a minimal set of orders to move from current → target
  - Apply liquidity and ADV guardrails
  - Send orders to the broker (Alpaca) or do a no-op if blocked

## 3. Key Assumptions & Limitations

1. **Market Structure**
   - Assumes ETFs (QQQ + inverse leg) remain highly liquid with deep books.
   - Assumes daily EOD execution approximates backtest assumptions.

2. **Data Quality**
   - Assumes stable daily OHLCV feeds with no frequent corruption.
   - Strategy is sensitive to missing or stale bars; guards exist, but behaviour is "no trade" rather than attempting to repair data.

3. **Execution Slippage**
   - Assumes slippage stays within historically observed bounds.
   - Adverse changes (e.g., lower liquidity, wider spreads) can materially reduce performance.

4. **Model Stability**
   - Signals are designed for NDX regime behaviour as observed historically.
   - Extreme structural changes to NDX/QQQ behaviour may degrade edge.

5. **Unleveraged / ETF Substitute Risk**
   - If using PSQ (or equivalent) instead of TQQQ/SQQQ, performance profile differs from original reference strategy (which used leveraged ETFs).
   - This is intentional to reduce risk, but means results are not directly comparable to the original leveraged backtest.

## 4. Model Risks

### 4.1 Market Risk

- **Directional Risk:** Strategy can be wrong on direction, leading to drawdowns.
- **Gap Risk:** Overnight gaps may invalidate EOD assumptions.
- **Volatility Regime Shifts:** Sudden spike in volatility (e.g., VIX shock) can harm both trend and MR legs.

**Mitigation:**
- Volatility filters (VIX / rolling vol).
- ATR-based position sizing.
- Non-leveraged implementation.

### 4.2 Liquidity & Execution Risk

- Large orders relative to ADV can move the market.
- Wider spreads or thin books near the close can cause poor slippage.

**Mitigation:**
- ADV-based checks and guardrail (GREEN/AMBER/RED).
- Optional ADV hard cap (block or scale orders).
- Slippage monitoring and drift detection vs baseline.

### 4.3 Data & Infrastructure Risk

- Incorrect bars, missing data, or API failures can cause bad decisions.
- Time sync / scheduling errors (e.g., running at wrong time).

**Mitigation:**
- Bar hygiene checks (last common date, volume sanity).
- Session guard (only runs at scheduled EOD window).
- No-op mode when data is stale, inconsistent, or fails validation.
- Daily replay pack + checksum of reports.

### 4.4 Model Implementation / Code Risk

- Bugs in code can cause:
  - incorrect exposure
  - incorrect interpretation of signals
  - missed orders or duplicate orders

**Mitigation:**
- Deterministic, unit-tested core components.
- Config snapshot hashing (config_hash16).
- Replay packs + replay viewer + replay diff.
- Broker reconciliation tool (internal vs Alpaca positions).

### 4.5 Operational Risk

- Environment drift (changing config, versions, or API keys).
- Manual changes at broker that are not reflected in model state.

**Mitigation:**
- Config hash stored in every run and replay pack.
- `replay_from_pack.py` and `make replay-latest` for environment checks.
- `reconcile_broker.py` and `make reconcile-broker` for position drift.

## 5. Controls & Guardrails

1. **Data Guardrails**
   - Bar hygiene (stale/mismatched date detection).
   - Volume sanity checks.
   - No-op if data invalid.

2. **Risk Guardrails**
   - ATR-based sizing.
   - Max position size as % of capital.
   - Turnover caps.
   - ADV guardrail (block/scale).
   - Liquidity depth classification (GREEN/AMBER/RED).

3. **Execution Guardrails**
   - Consolidated daily batch decision (no intra-day flipping).
   - Minimum trade size threshold to avoid dust trades.
   - Slippage monitoring + drift alerts.

4. **Governance & Audit**
   - Daily HTML reports.
   - Replay packs (JSON).
   - Replay viewer (HTML).
   - Replay diff (comparison of decisions across versions).
   - Monthly analytics reports.

5. **Reconciliation**
   - Internal vs broker reconciliation tool.
   - Non-zero exit on mismatches for automation/alerts.

## 6. Backtesting Summary (High-Level)

> Note: These are conceptual placeholders — actual results must be documented with precise stats.

- **Universe:** NDX/QQQ synthetic history, inverse leg synthetic where necessary.
- **Horizon:** ~40 years of NDX history (with synthetic ETF reconstruction).
- **Core Metrics:**
  - CAGR
  - Max drawdown
  - Volatility
  - Trade frequency
  - Worst multi-day loss sequences

**Limitations:**
- Synthetic ETF reconstruction introduces model risk.
- Transaction costs and slippage assumptions may differ from live.

## 7. Deployment & Change Management

- Any **material change** to:
  - signal formulas,
  - risk model,
  - guard logic,
  - universe,
  
  should result in a **model version bump** in `config/model_manifest.yaml`.

- For each change:
  - Document rationale.
  - Provide before/after backtest comparison.
  - Note expected impact on risk and return profile.

## 8. Known Failure Modes & Responses

1. **Data provider outage**
   - Behaviour: No-op for the day.
   - Action: Investigate, rerun if safe & data restored before close; otherwise accept missed day.

2. **Broker API outage or error**
   - Behaviour: System fails to place orders; positions remain as previous day.
   - Action: Manual review; compare broker vs internal using reconciliation tool.

3. **Config drift detected**
   - Behaviour: Replay tools and hashes indicate mismatch.
   - Action: Resolve config differences, re-run validation before continuing live trading.

4. **Unusually bad slippage / liquidity**
   - Behaviour: Slippage drift alert; liquidity metrics skewed.
   - Action: Consider reducing risk budget or pausing trading until conditions normalize.

## 9. Summary

RegimeFlex is a fully systematic, end-of-day long/short ETF strategy with:

- Defined signal logic (trend + regime-aware mean-reversion),
- Disciplined risk management (ATR sizing, filters, caps),
- Robust guardrails (data, liquidity, ADV, session),
- Strong observability (replay packs, reports, diffs, reconciliations).

This document serves as the primary model risk and system description reference. Any substantial change to model logic, risk engine, or universe should be accompanied by an update to this document and a new model version.

