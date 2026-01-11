#!/usr/bin/env python3
"""
Comprehensive test script for environment variable loading.

This script validates that:
1. The regimeflex package can be imported successfully
2. Environment variables are loaded automatically on import
3. All required API keys are accessible
4. APIKeys adapter works correctly
5. Alpaca SDK environment variables are set

This test is designed to be run in ANY context (Cursor, SSH, PM2, standalone Python)
to prove environment loading is working.

Usage:
    python scripts/test_env_loading.py
    # Or make executable:
    chmod +x scripts/test_env_loading.py
    ./scripts/test_env_loading.py
"""

import sys
import os
from pathlib import Path

# Add project root to path if running as script
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = []
        self.failed = []
    
    def add_pass(self, test_name: str, details: str = ""):
        """Record a passing test."""
        self.passed.append((test_name, details))
        print(f"✓ PASS: {test_name}")
        if details:
            print(f"    {details}")
    
    def add_fail(self, test_name: str, reason: str):
        """Record a failing test."""
        self.failed.append((test_name, reason))
        print(f"✗ FAIL: {test_name}")
        print(f"    Reason: {reason}")
    
    def summary(self) -> bool:
        """Print summary and return True if all tests passed."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Passed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        
        if self.failed:
            print("\nFailed Tests:")
            for test_name, reason in self.failed:
                print(f"  - {test_name}: {reason}")
            return False
        
        print("\n✓ ALL TESTS PASSED - Environment loading works correctly!")
        return True


def test_1_import_regimeflex(results: TestResult) -> bool:
    """Test 1: Import regimeflex (should auto-load .env)."""
    print("\n[Test 1] Importing regimeflex package...")
    try:
        import regimeflex
        results.add_pass("Import regimeflex", f"Version: {getattr(regimeflex, '__version__', 'unknown')}")
        return True
    except RuntimeError as e:
        # This is expected if .env is missing - regimeflex.__init__ raises RuntimeError
        if "Failed to load .env" in str(e) or "Missing required API keys" in str(e):
            results.add_fail("Import regimeflex", f"Environment not configured: {e}")
            return False
        results.add_fail("Import regimeflex", f"Unexpected RuntimeError: {e}")
        return False
    except Exception as e:
        results.add_fail("Import regimeflex", f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_env_loader_module(results: TestResult) -> bool:
    """Test 2: Verify env_loader module works."""
    print("\n[Test 2] Testing env_loader module...")
    try:
        from regimeflex.config.env_loader import load_environment, validate_required_keys
        
        # Test load_environment
        env_loaded = load_environment(verbose=False)
        if env_loaded:
            results.add_pass("load_environment()", "Environment loaded successfully")
        else:
            results.add_fail("load_environment()", "Failed to load .env file")
            return False
        
        # Test validate_required_keys
        keys_valid = validate_required_keys()
        if keys_valid:
            results.add_pass("validate_required_keys()", "All required keys present")
        else:
            results.add_fail("validate_required_keys()", "Missing required API keys")
            return False
        
        return True
    except Exception as e:
        results.add_fail("env_loader module", f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_direct_env_vars(results: TestResult) -> bool:
    """Test 3: Check environment variables are accessible."""
    print("\n[Test 3] Checking environment variables directly...")
    
    checks = {
        'ALPACA_KEY': os.getenv('ALPACA_KEY'),
        'APCA_API_KEY_ID': os.getenv('APCA_API_KEY_ID'),
        'ALPACA_SECRET': os.getenv('ALPACA_SECRET'),
        'APCA_API_SECRET_KEY': os.getenv('APCA_API_SECRET_KEY'),
        'POLYGON_KEY': os.getenv('POLYGON_KEY'),
        'POLYGON_API_KEY': os.getenv('POLYGON_API_KEY'),
    }
    
    # Check Alpaca Key (either name)
    alpaca_key = checks['ALPACA_KEY'] or checks['APCA_API_KEY_ID']
    if alpaca_key:
        results.add_pass("Alpaca Key", f"Found: {checks['ALPACA_KEY'] and 'ALPACA_KEY' or 'APCA_API_KEY_ID'}")
    else:
        results.add_fail("Alpaca Key", "Neither ALPACA_KEY nor APCA_API_KEY_ID found")
    
    # Check Alpaca Secret (either name)
    alpaca_secret = checks['ALPACA_SECRET'] or checks['APCA_API_SECRET_KEY']
    if alpaca_secret:
        results.add_pass("Alpaca Secret", f"Found: {checks['ALPACA_SECRET'] and 'ALPACA_SECRET' or 'APCA_API_SECRET_KEY'}")
    else:
        results.add_fail("Alpaca Secret", "Neither ALPACA_SECRET nor APCA_API_SECRET_KEY found")
    
    # Check Polygon Key (either name)
    polygon_key = checks['POLYGON_KEY'] or checks['POLYGON_API_KEY']
    if polygon_key:
        results.add_pass("Polygon Key", f"Found: {checks['POLYGON_KEY'] and 'POLYGON_KEY' or 'POLYGON_API_KEY'}")
    else:
        results.add_fail("Polygon Key", "Neither POLYGON_KEY nor POLYGON_API_KEY found")
    
    return bool(alpaca_key and alpaca_secret and polygon_key)


def test_4_api_keys_adapter(results: TestResult) -> bool:
    """Test 4: Test APIKeys adapter methods."""
    print("\n[Test 4] Testing APIKeys adapter...")
    try:
        from regimeflex.config.api_keys import APIKeys
        
        # Test alpaca_key_id()
        key_id = APIKeys.alpaca_key_id()
        if key_id:
            results.add_pass("APIKeys.alpaca_key_id()", f"Returns key (length: {len(key_id)})")
        else:
            results.add_fail("APIKeys.alpaca_key_id()", "Returns empty string")
        
        # Test alpaca_secret()
        secret = APIKeys.alpaca_secret()
        if secret:
            results.add_pass("APIKeys.alpaca_secret()", f"Returns secret (length: {len(secret)})")
        else:
            results.add_fail("APIKeys.alpaca_secret()", "Returns empty string")
        
        # Test alpaca_base_url()
        base_url = APIKeys.alpaca_base_url()
        if base_url:
            results.add_pass("APIKeys.alpaca_base_url()", f"Returns: {base_url}")
        else:
            results.add_fail("APIKeys.alpaca_base_url()", "Returns empty string")
        
        # Test polygon_key()
        polygon_key = APIKeys.polygon_key()
        if polygon_key:
            results.add_pass("APIKeys.polygon_key()", f"Returns key (length: {len(polygon_key)})")
        else:
            results.add_fail("APIKeys.polygon_key()", "Returns empty string")
        
        # Test telegram methods
        telegram_token = APIKeys.telegram_bot_token()
        telegram_chat_id = APIKeys.telegram_chat_id()
        if telegram_token:
            results.add_pass("APIKeys.telegram_bot_token()", "Returns token")
        else:
            results.add_pass("APIKeys.telegram_bot_token()", "Returns empty (optional)")
        
        if telegram_chat_id:
            results.add_pass("APIKeys.telegram_chat_id()", "Returns chat ID")
        else:
            results.add_pass("APIKeys.telegram_chat_id()", "Returns empty (optional)")
        
        return bool(key_id and secret and base_url and polygon_key)
    
    except Exception as e:
        results.add_fail("APIKeys adapter", f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_alpaca_sdk_env_vars(results: TestResult) -> bool:
    """Test 5: Verify Alpaca SDK environment variables are set."""
    print("\n[Test 5] Testing Alpaca SDK environment variable setup...")
    try:
        from regimeflex.config.api_keys import APIKeys
        
        # Call setup_alpaca_env() to ensure SDK vars are set
        APIKeys.setup_alpaca_env(verbose=False)
        
        # Check SDK environment variables
        sdk_key = os.getenv('APCA_API_KEY_ID')
        sdk_secret = os.getenv('APCA_API_SECRET_KEY')
        sdk_url = os.getenv('APCA_API_BASE_URL')
        
        if sdk_key:
            results.add_pass("APCA_API_KEY_ID set", f"Length: {len(sdk_key)}")
        else:
            results.add_fail("APCA_API_KEY_ID set", "Not found in environment")
        
        if sdk_secret:
            results.add_pass("APCA_API_SECRET_KEY set", f"Length: {len(sdk_secret)}")
        else:
            results.add_fail("APCA_API_SECRET_KEY set", "Not found in environment")
        
        if sdk_url:
            results.add_pass("APCA_API_BASE_URL set", f"Value: {sdk_url}")
        else:
            results.add_fail("APCA_API_BASE_URL set", "Not found in environment")
        
        return bool(sdk_key and sdk_secret and sdk_url)
    
    except Exception as e:
        results.add_fail("Alpaca SDK env vars", f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_exec_alpaca_integration(results: TestResult) -> bool:
    """Test 6: Test exec_alpaca integration with APIKeys."""
    print("\n[Test 6] Testing exec_alpaca integration...")
    try:
        from regimeflex.engine.exec_alpaca import get_alpaca_client_creds, AlpacaCreds
        
        creds = get_alpaca_client_creds()
        
        if not isinstance(creds, AlpacaCreds):
            results.add_fail("get_alpaca_client_creds()", f"Returns wrong type: {type(creds)}")
            return False
        
        if creds.key:
            results.add_pass("get_alpaca_client_creds().key", f"Present (length: {len(creds.key)})")
        else:
            results.add_fail("get_alpaca_client_creds().key", "Missing")
        
        if creds.secret:
            results.add_pass("get_alpaca_client_creds().secret", f"Present (length: {len(creds.secret)})")
        else:
            results.add_fail("get_alpaca_client_creds().secret", "Missing")
        
        if creds.base_url:
            results.add_pass("get_alpaca_client_creds().base_url", f"Value: {creds.base_url}")
        else:
            results.add_fail("get_alpaca_client_creds().base_url", "Missing")
        
        return bool(creds.key and creds.secret and creds.base_url)
    
    except Exception as e:
        results.add_fail("exec_alpaca integration", f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_env_file_location(results: TestResult) -> bool:
    """Test 7: Show where .env file was loaded from."""
    print("\n[Test 7] Checking .env file location...")
    try:
        from pathlib import Path
        from dotenv import find_dotenv
        
        # Try to find the .env file
        env_path = None
        found = find_dotenv()
        if found:
            env_path = Path(found)
        else:
            # Check explicit paths (same as env_loader.py)
            possible_paths = [
                Path(__file__).parent.parent / '.env',  # Project root
                Path.cwd() / '.env',  # Current working directory
                Path.home() / 'RegimeFlex' / '.env',  # VPS common location
            ]
            for path in possible_paths:
                if path.exists():
                    env_path = path
                    break
        
        if env_path and env_path.exists():
            results.add_pass(".env file location", f"Found at: {env_path}")
            return True
        else:
            # Check if env vars are set via PM2/system
            if os.getenv('ALPACA_KEY') or os.getenv('APCA_API_KEY_ID'):
                results.add_pass(".env file location", "Environment variables loaded from system/PM2")
                return True
            else:
                results.add_fail(".env file location", "No .env file found and no system env vars")
                return False
    
    except Exception as e:
        results.add_fail("env file location check", f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("RegimeFlex Environment Loading Test")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"Working Directory: {Path.cwd()}")
    print(f"Project Root: {Path(__file__).parent.parent}")
    
    results = TestResult()
    
    # Run all tests
    tests = [
        ("Import regimeflex", test_1_import_regimeflex),
        ("env_loader module", test_2_env_loader_module),
        ("Direct env vars", test_3_direct_env_vars),
        ("APIKeys adapter", test_4_api_keys_adapter),
        ("Alpaca SDK env vars", test_5_alpaca_sdk_env_vars),
        ("exec_alpaca integration", test_6_exec_alpaca_integration),
        ("Env file location", test_7_env_file_location),
    ]
    
    # Run tests (continue even if some fail)
    for test_name, test_func in tests:
        try:
            test_func(results)
        except Exception as e:
            results.add_fail(test_name, f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary and exit
    all_passed = results.summary()
    
    if not all_passed:
        print("\n" + "=" * 70)
        print("TROUBLESHOOTING")
        print("=" * 70)
        print("If tests failed, check:")
        print("  1. .env file exists in project root")
        print("  2. .env file contains required keys:")
        print("     - ALPACA_KEY or APCA_API_KEY_ID")
        print("     - ALPACA_SECRET or APCA_API_SECRET_KEY")
        print("     - POLYGON_KEY or POLYGON_API_KEY")
        print("  3. See env.example for template")
        print("  4. If using PM2, ensure environment variables are set in ecosystem.config.js")
        print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

