"""
Robust .env loader for RegimeFlex.

This module provides automatic environment variable loading with:
- Multi-path .env file discovery
- Required key validation
- Clear error messages
- Automatic loading on import

Usage:
    from regimeflex.config.env_loader import load_environment, validate_required_keys
    
    # Environment is automatically loaded on import
    # Or call explicitly:
    if load_environment():
        if validate_required_keys():
            # Proceed with application logic
            pass
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from dotenv import load_dotenv, find_dotenv
except ImportError:
    # Fallback if python-dotenv not installed
    def find_dotenv(*args, **kwargs):
        return None
    
    def load_dotenv(*args, **kwargs):
        return False


def _get_possible_env_paths() -> List[Path]:
    """
    Get list of possible .env file locations in priority order.
    
    Returns:
        List of Path objects to check for .env file
    """
    paths = []
    
    # 1. Use find_dotenv() to search up directory tree
    found = find_dotenv(usecwd=True)
    if found:
        paths.append(Path(found))
    
    # 2. Project root (regimeflex/config/env_loader.py -> project root)
    #    Path(__file__) = regimeflex/config/env_loader.py
    #    parent.parent.parent = project root
    config_file = Path(__file__)
    project_root = config_file.parent.parent.parent
    paths.append(project_root / ".env")
    
    # 3. Current working directory
    paths.append(Path.cwd() / ".env")
    
    # 4. Parent of current working directory (in case run from regimeflex/)
    paths.append(Path.cwd().parent / ".env")
    
    # 5. VPS common location: ~/RegimeFlex/.env
    paths.append(Path.home() / "RegimeFlex" / ".env")
    
    # 6. Alternative VPS location: ~/apps/RegimeFlex/.env
    paths.append(Path.home() / "apps" / "RegimeFlex" / ".env")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    return unique_paths


def load_environment(verbose: bool = True) -> bool:
    """
    Load .env file from multiple possible locations.
    
    Searches for .env file in this order:
    1. find_dotenv() result (searches up directory tree)
    2. Project root (regimeflex/config/env_loader.py -> project root)
    3. Current working directory
    4. Parent of current working directory
    5. ~/RegimeFlex/.env (VPS common location)
    6. ~/apps/RegimeFlex/.env (alternative VPS location)
    
    Args:
        verbose: If True, print success/error messages
        
    Returns:
        True if .env file was found and loaded, False otherwise
    """
    possible_paths = _get_possible_env_paths()
    
    for env_path in possible_paths:
        if env_path.exists() and env_path.is_file():
            # Load with override=True to ensure .env values take precedence
            result = load_dotenv(env_path, override=True)
            if result:
                if verbose:
                    print(f"✅ Loaded .env from: {env_path}")
                return True
    
    # No .env file found
    if verbose:
        print("⚠️  No .env file found. Checked locations:")
        for path in possible_paths:
            print(f"   - {path}")
        print("   Continuing with system environment variables only.")
    return False


def validate_required_keys(verbose: bool = True) -> Tuple[bool, List[str]]:
    """
    Validate that required environment variables are present.
    
    Checks for required keys with alternative names:
    - Alpaca Key: ALPACA_KEY or APCA_API_KEY_ID
    - Alpaca Secret: ALPACA_SECRET or APCA_API_SECRET_KEY
    - Polygon Key: POLYGON_KEY or POLYGON_API_KEY
    
    Args:
        verbose: If True, print error messages for missing keys
        
    Returns:
        Tuple of (is_valid, missing_keys_list)
        - is_valid: True if all required keys present, False otherwise
        - missing_keys_list: List of missing key names
    """
    missing = []
    
    # Check Alpaca Key
    alpaca_key = os.getenv("ALPACA_KEY") or os.getenv("APCA_API_KEY_ID")
    if not alpaca_key:
        missing.append("ALPACA_KEY (or APCA_API_KEY_ID)")
    
    # Check Alpaca Secret
    alpaca_secret = os.getenv("ALPACA_SECRET") or os.getenv("APCA_API_SECRET_KEY")
    if not alpaca_secret:
        missing.append("ALPACA_SECRET (or APCA_API_SECRET_KEY)")
    
    # Check Polygon Key (optional but recommended)
    polygon_key = os.getenv("POLYGON_KEY") or os.getenv("POLYGON_API_KEY")
    if not polygon_key:
        missing.append("POLYGON_KEY (or POLYGON_API_KEY) - optional but recommended")
    
    if missing:
        if verbose:
            print("❌ Missing required environment variables:")
            for key in missing:
                print(f"   - {key}")
            print("\n   Create a .env file or set these environment variables.")
            print("   See env.example for template.")
        return False, missing
    
    if verbose:
        print("✅ All required environment variables are set.")
    return True, []


def get_env_path() -> Optional[Path]:
    """
    Get the path to the .env file that was loaded (if any).
    
    Returns:
        Path to .env file if found, None otherwise
    """
    possible_paths = _get_possible_env_paths()
    for env_path in possible_paths:
        if env_path.exists() and env_path.is_file():
            return env_path
    return None


# Auto-load environment on import
# Use verbose=False to avoid spam when imported by other modules
# Individual modules can call load_environment(verbose=True) if they want messages
_load_result = load_environment(verbose=False)

# Export the load result for modules that want to check if .env was loaded
ENV_LOADED = _load_result
ENV_PATH = get_env_path()

