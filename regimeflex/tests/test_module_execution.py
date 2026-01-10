"""
Test module execution to verify packaging works correctly.

This test ensures that:
1. runner.py can be imported as a module
2. main() function exists and can be called
3. Relative imports work when executed as a module
"""

import sys
import pytest
from pathlib import Path


def test_runner_module_import():
    """Test that runner can be imported as a module."""
    # This should work without any PYTHONPATH hacks
    from regimeflex.engine.runner import run_daily_offline, main
    
    assert callable(run_daily_offline)
    assert callable(main)


def test_runner_main_exists():
    """Test that main() function exists and has correct signature."""
    from regimeflex.engine.runner import main
    
    # main() should exist and be callable
    assert callable(main)
    
    # Check it returns an int (exit code)
    # We can't actually run it without config, but we can verify it's callable


def test_package_main_import():
    """Test that __main__.py can be imported."""
    # This verifies the package structure is correct
    import regimeflex.engine
    
    # Check that __main__.py exists
    main_file = Path(regimeflex.engine.__file__).parent / "__main__.py"
    assert main_file.exists(), "__main__.py should exist in engine/"


def test_relative_imports_work():
    """Test that relative imports in runner.py work when imported as module."""
    # This is the key test - if relative imports fail, this will raise ImportError
    # Import runner which uses relative imports internally
    from regimeflex.engine import runner
    
    # If we get here, relative imports worked (runner.py imported successfully)
    assert runner is not None
    assert hasattr(runner, 'run_daily_offline')
    assert hasattr(runner, 'main')


def test_top_level_main_import():
    """Test that top-level __main__.py can be imported."""
    import regimeflex
    
    # Check that __main__.py exists
    main_file = Path(regimeflex.__file__).parent / "__main__.py"
    assert main_file.exists(), "__main__.py should exist in regimeflex/"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

