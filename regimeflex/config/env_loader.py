"""
Robust .env loader for RegimeFlex.

This module ensures environment variables are loaded correctly regardless of:
- Working directory (Cursor vs PM2 vs SSH)
- Execution method (module vs script vs entry point)
- Environment (dev vs production vs testing)

The .env file is automatically loaded when this module is imported.
"""
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


def load_environment(verbose: bool = True) -> bool:
    """
    Load .env file with robust path discovery.
    
    Searches multiple locations for .env file:
    1. Uses find_dotenv() to search parent directories automatically
    2. Falls back to explicit paths if find_dotenv() fails
    
    Args:
        verbose: If True, prints success/failure messages
        
    Returns:
        True if .env file was loaded, False otherwise
    """
    # Strategy 1: Use find_dotenv() (searches parent directories)
    env_path = find_dotenv()
    if env_path:
        load_dotenv(env_path, override=True)
        if verbose:
            print(f"✓ Loaded .env from {env_path}")
        return True
    
    # Strategy 2: Try explicit paths in order
    possible_paths = [
        Path(__file__).parent.parent.parent / '.env',  # Project root (3 levels up)
        Path.cwd() / '.env',  # Current working directory
        Path.home() / 'RegimeFlex' / '.env',  # VPS common location
    ]
    
    for path in possible_paths:
        if path.exists():
            load_dotenv(str(path), override=True)
            if verbose:
                print(f"✓ Loaded .env from {path}")
            return True
    
    # Strategy 3: Check if environment variables already present (PM2 loaded them)
    if os.getenv('ALPACA_KEY') or os.getenv('APCA_API_KEY_ID'):
        if verbose:
            print("✓ Environment variables already present (PM2 or system loaded)")
        return True
    
    # No .env found anywhere
    if verbose:
        print("⚠️  ERROR: No .env file found and no environment variables set!")
        print("Searched locations:")
        for path in possible_paths:
            print(f"  - {path} (exists: {path.exists()})")
    return False


def validate_required_keys() -> bool:
    """
    Verify all required API keys are present in environment.
    
    Checks for keys using alternative naming conventions:
    - ALPACA_KEY or APCA_API_KEY_ID
    - ALPACA_SECRET or APCA_API_SECRET_KEY
    - POLYGON_KEY or POLYGON_API_KEY
    
    Returns:
        True if all required keys present, False if any missing
    """
    required = {
        'Alpaca Key': ['ALPACA_KEY', 'APCA_API_KEY_ID'],
        'Alpaca Secret': ['ALPACA_SECRET', 'APCA_API_SECRET_KEY'],
        'Polygon Key': ['POLYGON_KEY', 'POLYGON_API_KEY'],
    }
    
    missing = []
    for name, keys in required.items():
        if not any(os.getenv(k) for k in keys):
            missing.append(f"{name} (checked: {' or '.join(keys)})")
    
    if missing:
        print("⚠️  Missing required environment variables:")
        for m in missing:
            print(f"  - {m}")
        print("\nPlease check your .env file contains these keys.")
        return False
    
    return True


# Auto-load environment on module import
# This ensures .env is loaded as soon as any code imports this module
if __name__ != '__main__':
    load_environment(verbose=False)
