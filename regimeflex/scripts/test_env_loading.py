#!/usr/bin/env python3
"""
Test environment variable loading outside of Cursor.

This script verifies that:
1. Importing regimeflex triggers environment loading
2. Environment variables are accessible
3. APIKeys adapter works correctly

Run this script from SSH or standalone Python to verify environment
loading works in clean Python processes (not just Cursor's terminal).

Usage:
    python regimeflex/scripts/test_env_loading.py
    # Or make executable:
    chmod +x regimeflex/scripts/test_env_loading.py
    ./regimeflex/scripts/test_env_loading.py
"""

import sys
from pathlib import Path

# Add project root to path if running as script
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_env_loading():
    """Test environment variable loading."""
    print("=" * 60)
    print("Environment Loading Test")
    print("=" * 60)
    
    # Test 1: Import triggers env loading
    print("\n[Test 1] Importing regimeflex...")
    try:
        import regimeflex
        print("✓ Import successful")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Check environment variables
    print("\n[Test 2] Checking environment variables...")
    import os
    
    keys_to_check = {
        'ALPACA_KEY or APCA_API_KEY_ID': bool(os.getenv('ALPACA_KEY') or os.getenv('APCA_API_KEY_ID')),
        'ALPACA_SECRET or APCA_API_SECRET_KEY': bool(os.getenv('ALPACA_SECRET') or os.getenv('APCA_API_SECRET_KEY')),
        'POLYGON_KEY': bool(os.getenv('POLYGON_KEY')),
    }
    
    all_present = True
    for key, present in keys_to_check.items():
        status = "✓" if present else "✗"
        print(f"  {status} {key}: {present}")
        if not present:
            all_present = False
    
    # Test 3: Validate using APIKeys module
    print("\n[Test 3] Testing APIKeys adapter...")
    try:
        from regimeflex.config.api_keys import APIKeys
        
        alpaca_key = APIKeys.alpaca_key_id()
        alpaca_secret = APIKeys.alpaca_secret()
        polygon_key = APIKeys.polygon_key()
        
        print(f"  Alpaca Key ID: {'✓' if alpaca_key else '✗'}")
        print(f"  Alpaca Secret: {'✓' if alpaca_secret else '✗'}")
        print(f"  Polygon Key: {'✓' if polygon_key else '✗'}")
        
        # Test setup_alpaca_env()
        print("\n[Test 4] Testing setup_alpaca_env()...")
        APIKeys.setup_alpaca_env()
        
        sdk_key = os.getenv('APCA_API_KEY_ID')
        sdk_secret = os.getenv('APCA_API_SECRET_KEY')
        sdk_url = os.getenv('APCA_API_BASE_URL')
        
        print(f"  APCA_API_KEY_ID: {'✓' if sdk_key else '✗'}")
        print(f"  APCA_API_SECRET_KEY: {'✓' if sdk_secret else '✗'}")
        print(f"  APCA_API_BASE_URL: {'✓' if sdk_url else '✗'}")
        
        if sdk_url:
            print(f"    Base URL: {sdk_url}")
        
    except Exception as e:
        print(f"✗ APIKeys test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test exec_alpaca import (uses APIKeys)
    print("\n[Test 5] Testing exec_alpaca import (uses APIKeys)...")
    try:
        from regimeflex.engine.exec_alpaca import get_alpaca_client_creds
        
        creds = get_alpaca_client_creds()
        print(f"  Credentials object created: ✓")
        print(f"  Key present: {'✓' if creds.key else '✗'}")
        print(f"  Secret present: {'✓' if creds.secret else '✗'}")
        print(f"  Base URL: {creds.base_url}")
        
    except Exception as e:
        print(f"✗ exec_alpaca import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Final result
    print("\n" + "=" * 60)
    if all_present:
        print("✓ ALL TESTS PASSED - Environment loading works!")
        print("\nNote: If keys are missing, create a .env file in the project root.")
        print("See env.example for template.")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Environment variables missing")
        print("\nThis is expected if:")
        print("  - No .env file exists")
        print("  - Environment variables not set")
        print("\nTo fix:")
        print("  1. Copy env.example to .env")
        print("  2. Fill in your API keys")
        print("  3. Run this test again")
        return False


if __name__ == '__main__':
    success = test_env_loading()
    sys.exit(0 if success else 1)

