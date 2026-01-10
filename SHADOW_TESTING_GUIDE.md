# Shadow Testing Implementation Guide

## Overview

Shadow testing compares outputs from old code paths vs new `core_logic.py` to ensure 100% mathematical parity before switching to the centralized implementation.

## Architecture

### Phase 1: Extraction ✅
- Created `regimeflex/engine/core_logic.py` with centralized functions
- All functions are pure and deterministic
- No side effects, suitable for shadow testing

### Phase 2: Shadow Testing ✅
- Created `regimeflex/engine/shadow_test.py` - Comparison framework
- Modified `portfolio.py` and `risk.py` to run both old and new code paths
- Added discrepancy checking with 0.0001% tolerance
- CRITICAL_ERROR logging on mismatches

## Shadow Testing Points

### 1. Safe Price Calculation
**Location**: `portfolio.py` - `compute_target_exposure()`
- **Old**: `get_safe_price()` from `bar_completeness.py`
- **New**: `get_safe_price_core()` from `core_logic.py`
- **Tests**: Price value, safety flag, reason string

### 2. Regime Detection with Hysteresis
**Location**: `portfolio.py` - `compute_target_exposure()`
- **Old**: `detect_regime_with_hysteresis()` from `regime_buffer.py`
- **New**: `detect_regime_with_hysteresis_core()` from `core_logic.py`
- **Tests**: Bull flag, reason string, regime state dict

### 3. Circuit Breakers
**Location**: `portfolio.py` and `risk.py`
- **Old**: `circuit_breakers()` from `risk.py`
- **New**: `circuit_breakers_core()` from `core_logic.py`
- **Tests**: Blocked flag, reason string

### 4. Position Sizing
**Location**: `risk.py` - `dynamic_position_size()`
- **Old**: Inline calculations in `dynamic_position_size()`
- **New**: `calculate_base_volatility_core()`, `calculate_regime_vol_adjustment_core()`, `calculate_decay_adjustment_core()`, `calculate_position_size_core()`
- **Tests**: Base vol, regime adjust, decay adjust, target dollars

## Tolerance Settings

- **Float Comparison**: 0.0001% (0.000001 absolute)
- **Boolean Comparison**: Exact match required
- **String Comparison**: Case-insensitive for reasons, exact for others

## Safety Features

1. **No Behavior Change**: Old code path always executes and returns
2. **CRITICAL_ERROR Logging**: Any mismatch triggers critical log
3. **Incident Logging**: Mismatches logged to incident system
4. **Non-Blocking**: Shadow test failures don't stop execution

## Running Tests

```bash
# Run shadow tests
pytest regimeflex/tests/test_core_logic_shadow.py -v

# Run with coverage
pytest regimeflex/tests/test_core_logic_shadow.py --cov=regimeflex.engine.core_logic --cov-report=html

# Run specific test
pytest regimeflex/tests/test_core_logic_shadow.py::TestPositionSizing::test_position_size_full -v
```

## Monitoring Shadow Tests

### In Production Logs
Look for:
- `SHADOW TEST FAILED:` - Critical errors
- `CRITICAL_ERROR` level logs
- Incident logs with "Shadow test mismatch"

### Expected Behavior
- **No mismatches**: Old and new code produce identical results
- **If mismatch occurs**: 
  1. CRITICAL_ERROR logged
  2. Incident created
  3. Old code path result used (system continues)
  4. Investigation required

## Phase 3: Discrepancy Check (Automatic)

The shadow testing framework automatically:
1. Runs both old and new code paths
2. Compares results with 0.0001% tolerance
3. Logs CRITICAL_ERROR if discrepancy > tolerance
4. Returns old code path result (no behavior change)

## Next Steps

1. **Run Tests**: Verify 100% parity
   ```bash
   pytest regimeflex/tests/test_core_logic_shadow.py -v
   ```

2. **Monitor Production**: Watch for shadow test failures in logs

3. **Fix Discrepancies**: If any mismatches found, investigate and fix

4. **Phase 3 (Future)**: Once verified, switch to new code path

## Troubleshooting

### Test Failures
- Check tolerance settings (may need adjustment)
- Verify input data matches between old/new
- Check for floating-point precision issues

### Production Mismatches
- Review CRITICAL_ERROR logs
- Check incident logs for details
- Compare old vs new results
- Investigate root cause

## Code Locations

- **Core Logic**: `regimeflex/engine/core_logic.py`
- **Shadow Framework**: `regimeflex/engine/shadow_test.py`
- **Tests**: `regimeflex/tests/test_core_logic_shadow.py`
- **Modified Files**: 
  - `regimeflex/engine/portfolio.py`
  - `regimeflex/engine/risk.py`

