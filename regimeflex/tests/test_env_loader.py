"""
Tests for regimeflex.config.env_loader module.

Tests environment loading, path discovery, and key validation.
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
    get_env_path,
    _get_possible_env_paths
)


def test_get_possible_env_paths():
    """Test that possible env paths are returned."""
    paths = _get_possible_env_paths()
    assert isinstance(paths, list)
    assert len(paths) > 0
    assert all(isinstance(p, Path) for p in paths)


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


def test_load_environment_without_env():
    """Test loading when no .env file exists."""
    # Mock find_dotenv to return None
    with patch('regimeflex.config.env_loader.find_dotenv', return_value=None):
        # Mock Path.exists() to return False for all paths
        with patch('pathlib.Path.exists', return_value=False):
            result = load_environment(verbose=False)
            assert result is False


def test_validate_required_keys_all_present():
    """Test validation when all required keys are present."""
    with patch.dict(os.environ, {
        'ALPACA_KEY': 'test_key',
        'ALPACA_SECRET': 'test_secret',
        'POLYGON_KEY': 'test_polygon'
    }):
        is_valid, missing = validate_required_keys(verbose=False)
        assert is_valid is True
        assert missing == []


def test_validate_required_keys_missing_alpaca():
    """Test validation when Alpaca keys are missing."""
    with patch.dict(os.environ, {
        'POLYGON_KEY': 'test_polygon'
    }, clear=True):
        is_valid, missing = validate_required_keys(verbose=False)
        assert is_valid is False
        assert len(missing) > 0
        assert any('ALPACA_KEY' in key for key in missing)


def test_validate_required_keys_alternative_names():
    """Test validation accepts alternative key names."""
    with patch.dict(os.environ, {
        'APCA_API_KEY_ID': 'test_key',  # Alternative name
        'APCA_API_SECRET_KEY': 'test_secret',  # Alternative name
        'POLYGON_API_KEY': 'test_polygon'  # Alternative name
    }, clear=True):
        is_valid, missing = validate_required_keys(verbose=False)
        assert is_valid is True
        assert missing == []


def test_get_env_path():
    """Test getting the path to loaded .env file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("TEST=value\n")
        
        with patch('regimeflex.config.env_loader._get_possible_env_paths', return_value=[env_file]):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    path = get_env_path()
                    assert path is not None
                    assert isinstance(path, Path)


def test_module_import():
    """Test that module can be imported without errors."""
    from regimeflex.config.env_loader import (
        load_environment,
        validate_required_keys,
        get_env_path,
        ENV_LOADED,
        ENV_PATH
    )
    
    assert callable(load_environment)
    assert callable(validate_required_keys)
    assert callable(get_env_path)
    assert isinstance(ENV_LOADED, bool)
    assert ENV_PATH is None or isinstance(ENV_PATH, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

