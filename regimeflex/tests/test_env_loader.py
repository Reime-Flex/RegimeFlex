"""
Tests for regimeflex.config.env_loader module.

Tests environment loading and key validation.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
from regimeflex.config.env_loader import (
    load_environment,
    validate_required_keys,
)


def test_load_environment_with_existing_env(tmp_path):
    """Test loading .env file when it exists."""
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text("ALPACA_KEY=test_key\nALPACA_SECRET=test_secret\n")

    # Change to temp directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Mock find_dotenv to return our temp file
        with patch('regimeflex.config.env_loader.find_dotenv', return_value=str(env_file)):
            result = load_environment(verbose=False)
            assert result is True
    finally:
        os.chdir(original_cwd)


def test_load_environment_with_railway_env():
    """Test loading when running on Railway platform."""
    with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}):
        result = load_environment(verbose=False)
        assert result is True


def test_load_environment_with_existing_env_vars():
    """Test loading when env vars are already present."""
    with patch.dict(os.environ, {'ALPACA_KEY': 'test_key'}):
        result = load_environment(verbose=False)
        assert result is True


def test_load_environment_without_env():
    """Test loading when no .env file exists."""
    # Clear relevant env vars and mock find_dotenv
    with patch.dict(os.environ, {}, clear=True):
        with patch('regimeflex.config.env_loader.find_dotenv', return_value=None):
            with patch('pathlib.Path.exists', return_value=False):
                result = load_environment(verbose=False)
                assert result is False


def test_validate_required_keys_all_present():
    """Test validation when all required keys are present."""
    with patch.dict(os.environ, {
        'ALPACA_KEY': 'test_key',
        'ALPACA_SECRET': 'test_secret',
        'POLYGON_KEY': 'test_polygon'
    }, clear=True):
        result = validate_required_keys()
        assert result is True


def test_validate_required_keys_missing_alpaca():
    """Test validation when Alpaca keys are missing."""
    with patch.dict(os.environ, {
        'POLYGON_KEY': 'test_polygon'
    }, clear=True):
        result = validate_required_keys()
        assert result is False


def test_validate_required_keys_alternative_names():
    """Test validation accepts alternative key names."""
    with patch.dict(os.environ, {
        'APCA_API_KEY_ID': 'test_key',  # Alternative name
        'APCA_API_SECRET_KEY': 'test_secret',  # Alternative name
        'POLYGON_API_KEY': 'test_polygon'  # Alternative name
    }, clear=True):
        result = validate_required_keys()
        assert result is True


def test_module_import():
    """Test that module can be imported without errors."""
    from regimeflex.config.env_loader import (
        load_environment,
        validate_required_keys,
    )

    assert callable(load_environment)
    assert callable(validate_required_keys)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
