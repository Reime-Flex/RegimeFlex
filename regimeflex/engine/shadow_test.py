"""
Shadow Testing Framework

Compares outputs from old code paths vs new core_logic.py to ensure 100% parity
before switching to the centralized implementation.
"""

from __future__ import annotations

from typing import Any, Tuple, Optional, Dict
from dataclasses import dataclass
import math

from .identity import RegimeFlexIdentity as RF


# Tolerance for floating-point comparisons
TOLERANCE_PCT = 0.0001  # 0.0001% = 0.000001 absolute
EPSILON_ABSOLUTE = 1e-6


@dataclass(frozen=True)
class ShadowTestResult:
    """Result of shadow test comparison."""
    match: bool
    old_value: Any
    new_value: Any
    discrepancy_pct: float
    error_message: Optional[str] = None


def compare_floats(
    old_val: float,
    new_val: float,
    tolerance_pct: float = TOLERANCE_PCT,
    field_name: str = "value"
) -> ShadowTestResult:
    """
    Compare two float values with percentage tolerance.
    
    Args:
        old_val: Value from old code path
        new_val: Value from new code path
        tolerance_pct: Tolerance percentage (default 0.0001%)
        field_name: Field name for error messages
    
    Returns:
        ShadowTestResult indicating if values match
    """
    # Handle NaN and Inf
    if math.isnan(old_val) and math.isnan(new_val):
        return ShadowTestResult(
            match=True,
            old_value=old_val,
            new_value=new_val,
            discrepancy_pct=0.0
        )
    
    if math.isnan(old_val) or math.isnan(new_val):
        return ShadowTestResult(
            match=False,
            old_value=old_val,
            new_value=new_val,
            discrepancy_pct=float('inf'),
            error_message=f"{field_name}: NaN mismatch (old={old_val}, new={new_val})"
        )
    
    if math.isinf(old_val) or math.isinf(new_val):
        if old_val == new_val:
            return ShadowTestResult(
                match=True,
                old_value=old_val,
                new_value=new_val,
                discrepancy_pct=0.0
            )
        return ShadowTestResult(
            match=False,
            old_value=old_val,
            new_value=new_val,
            discrepancy_pct=float('inf'),
            error_message=f"{field_name}: Inf mismatch (old={old_val}, new={new_val})"
        )
    
    # Handle zero or very small values
    if abs(old_val) < EPSILON_ABSOLUTE and abs(new_val) < EPSILON_ABSOLUTE:
        return ShadowTestResult(
            match=True,
            old_value=old_val,
            new_value=new_val,
            discrepancy_pct=0.0
        )
    
    # Calculate percentage discrepancy
    if abs(old_val) > EPSILON_ABSOLUTE:
        discrepancy_pct = abs((new_val - old_val) / old_val) * 100.0
    else:
        # Old value is zero, use absolute difference
        discrepancy_pct = abs(new_val) * 100.0 if abs(new_val) > EPSILON_ABSOLUTE else 0.0
    
    # Check if within tolerance
    match = discrepancy_pct <= tolerance_pct
    
    error_msg = None
    if not match:
        error_msg = (
            f"{field_name}: Discrepancy {discrepancy_pct:.6f}% "
            f"(old={old_val:.6f}, new={new_val:.6f}, tolerance={tolerance_pct:.6f}%)"
        )
    
    return ShadowTestResult(
        match=match,
        old_value=old_val,
        new_value=new_val,
        discrepancy_pct=discrepancy_pct,
        error_message=error_msg
    )


def compare_bools(
    old_val: bool,
    new_val: bool,
    field_name: str = "value"
) -> ShadowTestResult:
    """Compare two boolean values (must be exact match)."""
    match = old_val == new_val
    error_msg = None
    if not match:
        error_msg = f"{field_name}: Boolean mismatch (old={old_val}, new={new_val})"
    
    return ShadowTestResult(
        match=match,
        old_value=old_val,
        new_value=new_val,
        discrepancy_pct=0.0 if match else 100.0,
        error_message=error_msg
    )


def compare_strings(
    old_val: str,
    new_val: str,
    field_name: str = "value",
    case_sensitive: bool = True
) -> ShadowTestResult:
    """Compare two string values."""
    if not case_sensitive:
        old_val = old_val.lower()
        new_val = new_val.lower()
    
    match = old_val == new_val
    error_msg = None
    if not match:
        error_msg = f"{field_name}: String mismatch (old='{old_val}', new='{new_val}')"
    
    return ShadowTestResult(
        match=match,
        old_value=old_val,
        new_value=new_val,
        discrepancy_pct=0.0 if match else 100.0,
        error_message=error_msg
    )


def compare_dicts(
    old_dict: Dict[str, Any],
    new_dict: Dict[str, Any],
    float_fields: Optional[list[str]] = None,
    bool_fields: Optional[list[str]] = None,
    string_fields: Optional[list[str]] = None,
    ignore_fields: Optional[list[str]] = None
) -> Tuple[bool, list[str]]:
    """
    Compare two dictionaries field by field.
    
    Args:
        old_dict: Dictionary from old code path
        new_dict: Dictionary from new code path
        float_fields: List of fields to compare as floats
        bool_fields: List of fields to compare as booleans
        string_fields: List of fields to compare as strings
        ignore_fields: List of fields to ignore
    
    Returns:
        Tuple of (all_match, list_of_errors)
    """
    if ignore_fields is None:
        ignore_fields = []
    if float_fields is None:
        float_fields = []
    if bool_fields is None:
        bool_fields = []
    if string_fields is None:
        string_fields = []
    
    errors = []
    all_keys = set(old_dict.keys()) | set(new_dict.keys())
    
    for key in all_keys:
        if key in ignore_fields:
            continue
        
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)
        
        # Determine comparison type
        if key in float_fields:
            result = compare_floats(float(old_val or 0), float(new_val or 0), field_name=key)
        elif key in bool_fields:
            result = compare_bools(bool(old_val), bool(new_val), field_name=key)
        elif key in string_fields:
            result = compare_strings(str(old_val or ""), str(new_val or ""), field_name=key)
        else:
            # Default: exact match
            if old_val != new_val:
                errors.append(f"{key}: Mismatch (old={old_val}, new={new_val})")
                continue
        
        if not result.match:
            errors.append(result.error_message or f"{key}: Mismatch")
    
    return len(errors) == 0, errors


def log_shadow_mismatch(
    function_name: str,
    errors: list[str],
    old_result: Any,
    new_result: Any,
    critical: bool = True
) -> None:
    """
    Log shadow test mismatch as CRITICAL_ERROR.
    
    Args:
        function_name: Name of function being tested
        errors: List of error messages
        old_result: Result from old code path
        new_result: Result from new code path
        critical: If True, log as CRITICAL_ERROR
    """
    level = "CRITICAL_ERROR" if critical else "ERROR"
    
    error_msg = f"SHADOW TEST FAILED: {function_name}\n"
    error_msg += f"  Old result: {old_result}\n"
    error_msg += f"  New result: {new_result}\n"
    error_msg += "  Errors:\n"
    for err in errors:
        error_msg += f"    - {err}\n"
    
    RF.print_log(error_msg, level)
    
    # Also log to incident logger if available
    try:
        from .incident import IncidentLogger
        incidents = IncidentLogger()
        incidents.log(
            level,
            f"Shadow test mismatch in {function_name}",
            {
                "function": function_name,
                "errors": errors,
                "old_result": str(old_result),
                "new_result": str(new_result)
            }
        )
    except Exception:
        pass  # Non-blocking if incident logger unavailable

