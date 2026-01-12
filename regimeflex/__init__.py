"""
RegimeFlex Trading System

A systematic trading system with regime detection, risk management,
and real broker integration.

Environment variables are automatically loaded from .env on package import.
"""

# CRITICAL: Load environment variables FIRST before any other imports
from regimeflex.config.env_loader import load_environment, validate_required_keys

# Load .env file (searches multiple locations, or uses platform env vars)
env_loaded = load_environment(verbose=True)

# Validate required API keys are present (critical for trading)
if not validate_required_keys():
    # More helpful error message
    import os
    railway_env = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_STATIC_URL')
    
    error_msg = "Missing required API keys.\n"
    if railway_env:
        error_msg += "Running on Railway: Set environment variables in Railway dashboard.\n"
        error_msg += "Visit: https://railway.app/dashboard → Variables tab\n"
    else:
        error_msg += "Please check your .env file or set environment variables.\n"
    
    error_msg += "\nRequired variables:\n"
    error_msg += "  - ALPACA_KEY or APCA_API_KEY_ID\n"
    error_msg += "  - ALPACA_SECRET or APCA_API_SECRET_KEY\n"
    error_msg += "  - POLYGON_KEY\n"
    
    raise RuntimeError(error_msg)

# Package metadata
__version__ = "30.0.0"
__author__ = "RegimeFlex Team"

# Now safe to import other modules that depend on environment variables
# (Future imports can be added here)
