"""
Tests for regimeflex.config.api_keys module.

Tests API key access, name normalization, and environment setup.
"""

import os
import pytest
from unittest.mock import patch

from regimeflex.config.api_keys import APIKeys, ALPACA_PAPER_URL, ALPACA_LIVE_URL


def test_alpaca_key_id_custom_name():
    """Test getting Alpaca key using custom name."""
    with patch.dict(os.environ, {'ALPACA_KEY': 'test_key_custom'}, clear=True):
        assert APIKeys.alpaca_key_id() == 'test_key_custom'


def test_alpaca_key_id_official_name():
    """Test getting Alpaca key using official SDK name."""
    with patch.dict(os.environ, {'APCA_API_KEY_ID': 'test_key_official'}, clear=True):
        assert APIKeys.alpaca_key_id() == 'test_key_official'


def test_alpaca_key_id_priority():
    """Test that official name takes priority over custom name."""
    with patch.dict(os.environ, {
        'APCA_API_KEY_ID': 'official_key',
        'ALPACA_KEY': 'custom_key'
    }, clear=True):
        assert APIKeys.alpaca_key_id() == 'official_key'


def test_alpaca_secret_custom_name():
    """Test getting Alpaca secret using custom name."""
    with patch.dict(os.environ, {'ALPACA_SECRET': 'test_secret_custom'}, clear=True):
        assert APIKeys.alpaca_secret() == 'test_secret_custom'


def test_alpaca_secret_official_name():
    """Test getting Alpaca secret using official SDK name."""
    with patch.dict(os.environ, {'APCA_API_SECRET_KEY': 'test_secret_official'}, clear=True):
        assert APIKeys.alpaca_secret() == 'test_secret_official'


def test_alpaca_base_url_default():
    """Test that base URL defaults to paper trading URL."""
    with patch.dict(os.environ, {}, clear=True):
        assert APIKeys.alpaca_base_url() == ALPACA_PAPER_URL


def test_alpaca_base_url_custom():
    """Test getting base URL using custom name."""
    custom_url = 'https://custom.alpaca.markets'
    with patch.dict(os.environ, {'ALPACA_BASE_URL': custom_url}, clear=True):
        assert APIKeys.alpaca_base_url() == custom_url


def test_alpaca_base_url_official():
    """Test getting base URL using official SDK name."""
    official_url = 'https://official.alpaca.markets'
    with patch.dict(os.environ, {'APCA_API_BASE_URL': official_url}, clear=True):
        assert APIKeys.alpaca_base_url() == official_url


def test_polygon_key():
    """Test getting Polygon key."""
    with patch.dict(os.environ, {'POLYGON_KEY': 'test_polygon'}, clear=True):
        assert APIKeys.polygon_key() == 'test_polygon'


def test_polygon_key_alternative():
    """Test getting Polygon key using alternative name."""
    with patch.dict(os.environ, {'POLYGON_API_KEY': 'test_polygon_alt'}, clear=True):
        assert APIKeys.polygon_key() == 'test_polygon_alt'


def test_setup_alpaca_env_sets_missing():
    """Test that setup_alpaca_env() sets missing SDK variables."""
    with patch.dict(os.environ, {
        'ALPACA_KEY': 'test_key',
        'ALPACA_SECRET': 'test_secret',
        'ALPACA_BASE_URL': 'https://test.alpaca.markets'
    }, clear=True):
        APIKeys.setup_alpaca_env()
        
        assert os.getenv('APCA_API_KEY_ID') == 'test_key'
        assert os.getenv('APCA_API_SECRET_KEY') == 'test_secret'
        assert os.getenv('APCA_API_BASE_URL') == 'https://test.alpaca.markets'


def test_setup_alpaca_env_preserves_existing():
    """Test that setup_alpaca_env() doesn't override existing SDK variables."""
    with patch.dict(os.environ, {
        'APCA_API_KEY_ID': 'existing_key',
        'ALPACA_KEY': 'custom_key'
    }, clear=True):
        APIKeys.setup_alpaca_env()
        
        # Should preserve existing SDK variable
        assert os.getenv('APCA_API_KEY_ID') == 'existing_key'


def test_has_alpaca_credentials():
    """Test has_alpaca_credentials() check."""
    with patch.dict(os.environ, {
        'ALPACA_KEY': 'test_key',
        'ALPACA_SECRET': 'test_secret'
    }, clear=True):
        assert APIKeys.has_alpaca_credentials() is True
    
    with patch.dict(os.environ, {'ALPACA_KEY': 'test_key'}, clear=True):
        assert APIKeys.has_alpaca_credentials() is False


def test_has_polygon_key():
    """Test has_polygon_key() check."""
    with patch.dict(os.environ, {'POLYGON_KEY': 'test_polygon'}, clear=True):
        assert APIKeys.has_polygon_key() is True
    
    with patch.dict(os.environ, {}, clear=True):
        assert APIKeys.has_polygon_key() is False


def test_has_telegram_credentials():
    """Test has_telegram_credentials() check."""
    with patch.dict(os.environ, {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id'
    }, clear=True):
        assert APIKeys.has_telegram_credentials() is True
    
    with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}, clear=True):
        assert APIKeys.has_telegram_credentials() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

