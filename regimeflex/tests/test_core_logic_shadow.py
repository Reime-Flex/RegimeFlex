"""
Unit Tests for Core Logic Shadow Testing

Tests ensure 100% mathematical parity between old code paths and new core_logic.py.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from regimeflex.engine.core_logic import (
    get_safe_price_core,
    detect_regime_core,
    detect_regime_with_hysteresis_core,
    calculate_base_volatility_core,
    calculate_regime_vol_adjustment_core,
    calculate_decay_adjustment_core,
    calculate_position_size_core,
    circuit_breakers_core
)
from regimeflex.engine.bar_completeness import get_safe_price
from regimeflex.engine.signals import detect_regime
from regimeflex.engine.regime_buffer import detect_regime_with_hysteresis
from regimeflex.engine.risk import _base_vol, dynamic_position_size, RiskInputs, RiskConfig, circuit_breakers
from regimeflex.engine.shadow_test import compare_floats, compare_bools, TOLERANCE_PCT


class TestSafePrice:
    """Test safe price calculation parity."""
    
    def test_safe_price_complete_bar(self):
        """Test with complete bar (yesterday's data)."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100.0 + i for i in range(10)]
        }, index=dates)
        
        # Old code path
        old_price, old_safe, old_reason = get_safe_price(df, use_t1_if_incomplete=True, fallback_to_last=False)
        
        # New code path
        new_result = get_safe_price_core(df, use_t1_if_incomplete=True, fallback_to_last=False)
        
        # Compare
        price_result = compare_floats(old_price, new_result.price, field_name="price")
        safe_result = compare_bools(old_safe, new_result.is_safe, field_name="is_safe")
        
        assert price_result.match, f"Price mismatch: {price_result.error_message}"
        assert safe_result.match, f"Safety mismatch: {safe_result.error_message}"
    
    def test_safe_price_incomplete_bar(self):
        """Test with incomplete bar (today's data)."""
        dates = pd.date_range(end=datetime.now(timezone.utc), periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100.0 + i for i in range(10)]
        }, index=dates)
        
        # Old code path
        old_price, old_safe, old_reason = get_safe_price(df, use_t1_if_incomplete=True, fallback_to_last=False)
        
        # New code path
        new_result = get_safe_price_core(df, use_t1_if_incomplete=True, fallback_to_last=False)
        
        # Compare
        price_result = compare_floats(old_price, new_result.price, field_name="price")
        safe_result = compare_bools(old_safe, new_result.is_safe, field_name="is_safe")
        
        assert price_result.match, f"Price mismatch: {price_result.error_message}"
        assert safe_result.match, f"Safety mismatch: {safe_result.error_message}"


class TestRegimeDetection:
    """Test regime detection parity."""
    
    def test_detect_regime_basic(self):
        """Test basic regime detection."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=250, freq='D')
        close_prices = pd.Series([100.0 + (i * 0.1) for i in range(250)], index=dates)
        
        # Old code path
        old_regime = detect_regime(close_prices, slow=200, require_complete_bar=True)
        
        # New code path
        new_regime = detect_regime_core(close_prices, slow=200, require_complete_bar=True)
        
        # Compare
        bull_match = compare_bools(old_regime.bull, new_regime.bull, field_name="bull")
        assert bull_match.match, f"Bull mismatch: {bull_match.error_message}"
        
        # Compare rvol (may be None)
        if old_regime.qqq_rvol_20 is not None and new_regime.qqq_rvol_20 is not None:
            rvol_match = compare_floats(old_regime.qqq_rvol_20, new_regime.qqq_rvol_20, field_name="rvol_20")
            assert rvol_match.match, f"Rvol mismatch: {rvol_match.error_message}"
    
    def test_detect_regime_with_hysteresis(self):
        """Test regime detection with hysteresis."""
        qqq_close = 150.0
        slow_ma = 140.0
        current_state = {"confirmed_regime": None, "since_date": None, "consecutive_days": 0}
        
        # Old code path
        old_bull, old_reason, old_state = detect_regime_with_hysteresis(
            qqq_close, slow_ma, current_state, buffer_pct=0.02, confirmation_days=2
        )
        
        # New code path
        new_bull, new_reason, new_state = detect_regime_with_hysteresis_core(
            qqq_close, slow_ma, current_state, buffer_pct=0.02, confirmation_days=2
        )
        
        # Compare
        bull_match = compare_bools(old_bull, new_bull, field_name="is_bull")
        assert bull_match.match, f"Bull mismatch: {bull_match.error_message}"
        
        # Compare state (handle both bool and string formats)
        old_confirmed = old_state.get("confirmed_regime")
        new_confirmed = new_state.get("confirmed_regime")
        # Normalize to bool for comparison
        old_bool = bool(old_confirmed) if not isinstance(old_confirmed, str) else (old_confirmed == "BULL")
        new_bool = bool(new_confirmed) if not isinstance(new_confirmed, str) else (new_confirmed == "BULL")
        assert old_bool == new_bool, \
            f"Confirmed regime mismatch: {old_state} vs {new_state}"


class TestPositionSizing:
    """Test position sizing calculation parity."""
    
    def test_base_volatility(self):
        """Test base volatility calculation."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=20, freq='D')
        close = pd.Series([100.0 + (i * 0.5) for i in range(20)], index=dates)
        high = close * 1.02
        low = close * 0.98
        
        # Old code path
        old_base_vol = _base_vol(close, high, low, atr_len=14)
        
        # New code path
        new_base_vol = calculate_base_volatility_core(close, high, low, atr_len=14)
        
        # Compare
        base_vol_match = compare_floats(old_base_vol, new_base_vol, field_name="base_vol")
        assert base_vol_match.match, f"Base vol mismatch: {base_vol_match.error_message}"
    
    def test_regime_vol_adjustment(self):
        """Test regime volatility adjustment."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=25, freq='D')
        qqq_close = pd.Series([100.0 + (i * 0.1) for i in range(25)], index=dates)
        
        # Test case 1: Normal VIX
        old_adj = 1.0
        if 20 > 25:
            old_adj = 0.7
        rvol20 = qqq_close.pct_change().rolling(20).std() * np.sqrt(252)
        if pd.notna(rvol20.iloc[-1]) and float(rvol20.iloc[-1]) > 0.25:
            old_adj = min(old_adj, 0.5)
        
        new_adj = calculate_regime_vol_adjustment_core(vix=20.0, qqq_close=qqq_close, is_opex=False)
        
        adj_match = compare_floats(old_adj, new_adj, field_name="regime_vol_adjust")
        assert adj_match.match, f"Regime vol adjust mismatch: {adj_match.error_message}"
    
    def test_decay_adjustment(self):
        """Test decay adjustment calculation."""
        # Test case 1: No decay
        old_adj = 1.0
        new_adj = calculate_decay_adjustment_core(None)
        assert abs(old_adj - new_adj) < 1e-6, f"Decay adjust mismatch: {old_adj} vs {new_adj}"
        
        # Test case 2: Low decay (< 1%)
        decay_stats = {"period_decay_pct": 0.5}
        old_adj = 1.0
        new_adj = calculate_decay_adjustment_core(decay_stats)
        assert abs(old_adj - new_adj) < 1e-6, f"Decay adjust mismatch: {old_adj} vs {new_adj}"
        
        # Test case 3: High decay (> 1%)
        decay_stats = {"period_decay_pct": 2.0}
        period_decay = 2.0
        old_adj = max(0.7, 1.0 - (period_decay / 10.0))  # Should be 0.8
        new_adj = calculate_decay_adjustment_core(decay_stats)
        adj_match = compare_floats(old_adj, new_adj, field_name="decay_adjust")
        assert adj_match.match, f"Decay adjust mismatch: {adj_match.error_message}"
    
    def test_position_size_full(self):
        """Test full position sizing calculation."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=20, freq='D')
        close = pd.Series([100.0 + (i * 0.5) for i in range(20)], index=dates)
        high = close * 1.02
        low = close * 0.98
        qqq_close = pd.Series([100.0 + (i * 0.1) for i in range(25)], index=pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=25, freq='D'))
        
        equity = 25000.0
        cfg = RiskConfig()
        inputs = RiskInputs(
            equity=equity,
            price=close.iloc[-1],
            vix=20.0,
            qqq_close=qqq_close,
            is_fomc_window=False,
            is_opex=False
        )
        
        # Old code path
        old_dollars, old_note = dynamic_position_size(inputs, close, high, low, cfg, decay_stats=None)
        
        # New code path
        base_vol = calculate_base_volatility_core(close, high, low, cfg.atr_len)
        regime_adj = calculate_regime_vol_adjustment_core(inputs.vix, inputs.qqq_close, False)
        decay_adj = calculate_decay_adjustment_core(None)
        new_result = calculate_position_size_core(
            equity=equity,
            base_vol=base_vol,
            risk_budget_pct=cfg.risk_budget_pct,
            regime_vol_adjust=regime_adj,
            decay_adjust=decay_adj,
            max_position_pct=cfg.max_position_pct,
            is_opex=False
        )
        
        # Compare
        dollars_match = compare_floats(old_dollars, new_result.target_dollars, field_name="target_dollars")
        assert dollars_match.match, f"Position size mismatch: {dollars_match.error_message}"


class TestCircuitBreakers:
    """Test circuit breakers parity."""
    
    def test_circuit_breakers_normal(self):
        """Test circuit breakers in normal conditions."""
        dates = pd.date_range(end=datetime.now(timezone.utc) - timedelta(days=1), periods=25, freq='D')
        qqq_close = pd.Series([100.0 + (i * 0.1) for i in range(25)], index=dates)
        cfg = RiskConfig()
        inputs = RiskInputs(
            equity=25000.0,
            price=100.0,
            vix=20.0,
            qqq_close=qqq_close,
            is_fomc_window=False,
            is_opex=False
        )
        
        # Old code path
        old_blocked, old_reason = circuit_breakers(inputs, cfg)
        
        # New code path
        new_blocked, new_reason = circuit_breakers_core(
            vix=20.0,
            qqq_close=qqq_close,
            vix_hard=cfg.vix_hard,
            qqq_20d_vol_max=cfg.qqq_20d_vol_max,
            is_fomc_window=False,
            is_opex=False
        )
        
        # Compare
        blocked_match = compare_bools(old_blocked, new_blocked, field_name="blocked")
        assert blocked_match.match, f"Blocked mismatch: {blocked_match.error_message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

