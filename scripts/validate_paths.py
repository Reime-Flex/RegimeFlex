#!/usr/bin/env python3
"""
Validation script for regimeflex/config/paths.py

Tests all acceptance criteria for Task 2.2.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_acceptance_criteria():
    """Test all acceptance criteria."""
    print("=" * 70)
    print("Path Constants Module Validation")
    print("=" * 70)
    
    results = {
        'passed': [],
        'failed': []
    }
    
    # Test 1: File exists
    print("\n[Test 1] File exists at regimeflex/config/paths.py")
    paths_file = project_root / 'regimeflex' / 'config' / 'paths.py'
    if paths_file.exists():
        results['passed'].append("File exists")
        print("✓ PASS: File exists")
    else:
        results['failed'].append("File does not exist")
        print("✗ FAIL: File does not exist")
        return False
    
    # Test 2: Can import without errors
    print("\n[Test 2] Can import without errors")
    try:
        # Import directly to avoid __init__.py environment loading
        import importlib.util
        spec = importlib.util.spec_from_file_location("paths", paths_file)
        paths_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(paths_module)
        results['passed'].append("Import successful")
        print("✓ PASS: Import successful")
    except Exception as e:
        results['failed'].append(f"Import failed: {e}")
        print(f"✗ FAIL: Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: PROJECT_ROOT calculated correctly
    print("\n[Test 3] PROJECT_ROOT calculated correctly (3 levels up)")
    project_root_actual = paths_module.PROJECT_ROOT
    expected_root = paths_file.parent.parent.parent
    
    if project_root_actual.resolve() == expected_root.resolve():
        results['passed'].append("PROJECT_ROOT correct")
        print(f"✓ PASS: PROJECT_ROOT = {project_root_actual}")
        print(f"  Expected: {expected_root}")
        print(f"  Match: {project_root_actual.resolve() == expected_root.resolve()}")
    else:
        results['failed'].append(f"PROJECT_ROOT incorrect: {project_root_actual} != {expected_root}")
        print(f"✗ FAIL: PROJECT_ROOT mismatch")
        print(f"  Got: {project_root_actual}")
        print(f"  Expected: {expected_root}")
    
    if not project_root_actual.is_absolute():
        results['failed'].append("PROJECT_ROOT is not absolute")
        print("✗ FAIL: PROJECT_ROOT is not absolute")
    else:
        results['passed'].append("PROJECT_ROOT is absolute")
        print("✓ PASS: PROJECT_ROOT is absolute")
    
    # Test 4: All directory constants defined
    print("\n[Test 4] All directory constants defined")
    required_dirs = [
        'DATA_DIR', 'STATE_DIR', 'CONFIG_DIR', 'LOGS_DIR', 'REPORTS_DIR',
        'REPLAYS_DIR', 'CACHE_DIR', 'LOGS_TRADING_DIR', 'LOGS_AUDIT_DIR',
        'LOGS_DECAY_DIR', 'LOGS_INCIDENTS_DIR', 'REPORTS_MONTHLY_DIR'
    ]
    for dir_name in required_dirs:
        if hasattr(paths_module, dir_name):
            dir_path = getattr(paths_module, dir_name)
            if dir_path.is_absolute():
                results['passed'].append(f"{dir_name} defined and absolute")
                print(f"✓ PASS: {dir_name} = {dir_path}")
            else:
                results['failed'].append(f"{dir_name} is not absolute")
                print(f"✗ FAIL: {dir_name} is not absolute: {dir_path}")
        else:
            results['failed'].append(f"{dir_name} not defined")
            print(f"✗ FAIL: {dir_name} not defined")
    
    # Test 5: All state file constants defined
    print("\n[Test 5] All state file constants defined")
    required_state_files = [
        'RUN_LOCK_FILE', 'POSITIONS_FILE', 'KILL_SWITCH_FILE',
        'KILL_SWITCH_FLAG_FILE', 'REGIME_STATE_FILE', 'ORDER_WAL_FILE',
        'TRADING_STATE_FILE', 'GUARDIAN_HEARTBEAT_FILE'
    ]
    for file_name in required_state_files:
        if hasattr(paths_module, file_name):
            file_path = getattr(paths_module, file_name)
            if file_path.is_absolute():
                results['passed'].append(f"{file_name} defined and absolute")
                print(f"✓ PASS: {file_name} = {file_path}")
            else:
                results['failed'].append(f"{file_name} is not absolute")
                print(f"✗ FAIL: {file_name} is not absolute: {file_path}")
        else:
            results['failed'].append(f"{file_name} not defined")
            print(f"✗ FAIL: {file_name} not defined")
    
    # Test 6: All config file constants defined
    print("\n[Test 6] All config file constants defined")
    required_config_files = [
        'RISK_CONFIG', 'EXPOSURE_CONFIG', 'SCHEDULE_CONFIG',
        'TELEMETRY_CONFIG', 'DATA_CONFIG', 'BROKER_CONFIG',
        'METRICS_CONFIG', 'LOGS_CONFIG', 'REPORTS_CONFIG',
        'SAFETY_CONFIG', 'US_HOLIDAYS_CONFIG', 'US_HALFDAYS_CONFIG'
    ]
    for file_name in required_config_files:
        if hasattr(paths_module, file_name):
            file_path = getattr(paths_module, file_name)
            if file_path.is_absolute():
                results['passed'].append(f"{file_name} defined and absolute")
                print(f"✓ PASS: {file_name} = {file_path}")
            else:
                results['failed'].append(f"{file_name} is not absolute")
                print(f"✗ FAIL: {file_name} is not absolute: {file_path}")
        else:
            results['failed'].append(f"{file_name} not defined")
            print(f"✗ FAIL: {file_name} not defined")
    
    # Test 7: Helper functions implemented
    print("\n[Test 7] Helper functions implemented")
    required_functions = [
        'get_log_file', 'get_report_file', 'get_incident_file',
        'get_replay_file', 'ensure_directories', 'print_paths'
    ]
    for func_name in required_functions:
        if hasattr(paths_module, func_name):
            func = getattr(paths_module, func_name)
            if callable(func):
                results['passed'].append(f"{func_name} implemented")
                print(f"✓ PASS: {func_name} is callable")
            else:
                results['failed'].append(f"{func_name} is not callable")
                print(f"✗ FAIL: {func_name} is not callable")
        else:
            results['failed'].append(f"{func_name} not defined")
            print(f"✗ FAIL: {func_name} not defined")
    
    # Test 8: Directories created automatically on import
    print("\n[Test 8] Directories created automatically on import")
    test_dirs = [
        paths_module.DATA_DIR,
        paths_module.STATE_DIR,
        paths_module.LOGS_DIR,
        paths_module.CACHE_DIR,
    ]
    all_exist = True
    for dir_path in test_dirs:
        if dir_path.exists() and dir_path.is_dir():
            results['passed'].append(f"{dir_path.name} directory exists")
            print(f"✓ PASS: {dir_path.name} exists")
        else:
            results['failed'].append(f"{dir_path.name} directory does not exist")
            print(f"✗ FAIL: {dir_path.name} does not exist: {dir_path}")
            all_exist = False
    
    # Test 9: print_paths() diagnostic function works
    print("\n[Test 9] print_paths() diagnostic function works")
    try:
        print("\n--- print_paths() output ---")
        paths_module.print_paths()
        print("--- end print_paths() output ---\n")
        results['passed'].append("print_paths() works")
        print("✓ PASS: print_paths() executed successfully")
    except Exception as e:
        results['failed'].append(f"print_paths() failed: {e}")
        print(f"✗ FAIL: print_paths() failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results['failed']:
        print("\nFailed Tests:")
        for failure in results['failed']:
            print(f"  - {failure}")
        return False
    
    print("\n✓ ALL ACCEPTANCE CRITERIA MET!")
    return True


if __name__ == '__main__':
    success = test_acceptance_criteria()
    sys.exit(0 if success else 1)

