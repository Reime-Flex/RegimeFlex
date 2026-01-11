"""
RegimeFlex Trading System

A systematic trading system with regime detection, risk management,
and real broker integration.
"""

# Load environment FIRST before any other imports
# This ensures .env is loaded before any module accesses environment variables
from regimeflex.config.env_loader import load_environment, validate_required_keys

# Load .env file automatically on package import
# This runs whenever someone imports regimeflex
if not load_environment(verbose=True):
    import warnings
    warnings.warn(
        "Failed to load .env file. RegimeFlex will use system environment variables only. "
        "Create a .env file in the project root or set environment variables manually.",
        UserWarning
    )

# Validate required API keys
# Note: We warn instead of raising to allow partial imports for testing
is_valid, missing_keys = validate_required_keys(verbose=True)
if not is_valid:
    import warnings
    warnings.warn(
        f"Missing required API keys: {', '.join(missing_keys)}. "
        "Some RegimeFlex features may not work. See env.example for required keys.",
        UserWarning
    )

# Now safe to import other modules that might need environment variables
# Additional imports can be added here as needed

__version__ = "30.0.0"
__author__ = "RegimeFlex Team"
