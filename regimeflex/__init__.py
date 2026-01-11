"""
RegimeFlex Trading System

A systematic trading system with regime detection, risk management,
and real broker integration.

Environment variables are automatically loaded from .env on package import.
"""

# CRITICAL: Load environment variables FIRST before any other imports
from regimeflex.config.env_loader import load_environment, validate_required_keys

# Load .env file (searches multiple locations)
if not load_environment(verbose=True):
    raise RuntimeError(
        "Failed to load .env file. Please ensure .env exists in project root "
        "or environment variables are set."
    )

# Validate required API keys are present
if not validate_required_keys():
    raise RuntimeError(
        "Missing required API keys. Please check your .env file contains:\n"
        "  - ALPACA_KEY or APCA_API_KEY_ID\n"
        "  - ALPACA_SECRET or APCA_API_SECRET_KEY\n"
        "  - POLYGON_KEY or POLYGON_API_KEY"
    )

# Package metadata
__version__ = "30.0.0"
__author__ = "RegimeFlex Team"

# Now safe to import other modules that depend on environment variables
# (Future imports can be added here)
