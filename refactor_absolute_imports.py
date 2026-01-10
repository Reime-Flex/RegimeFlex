#!/usr/bin/env python3
"""
Script to convert relative imports to absolute imports in RegimeFlex codebase.

This script:
1. Scans all Python files for relative imports (from . import ...)
2. Converts them to absolute imports (from regimeflex.engine import ...)
3. Preserves the file structure and other code

Usage:
    python refactor_absolute_imports.py [--dry-run] [--file <path>]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

def get_package_path(file_path: Path) -> str:
    """Determine the package path for a file."""
    parts = file_path.parts
    if 'regimeflex' not in parts:
        return None
    
    # Find regimeflex index
    regimeflex_idx = parts.index('regimeflex')
    
    # Get path after regimeflex
    if len(parts) > regimeflex_idx + 1:
        subpath = '.'.join(parts[regimeflex_idx + 1:-1])  # Exclude filename
        if subpath:
            return f"regimeflex.{subpath}"
        else:
            return "regimeflex"
    return "regimeflex"

def convert_relative_import(line: str, file_path: Path) -> str:
    """Convert a relative import to absolute import."""
    # Match: from .module import ...
    match = re.match(r'^(\s*)from\s+\.([^\s]+)\s+import\s+(.+)$', line)
    if match:
        indent = match.group(1)
        module = match.group(2)
        imports = match.group(3)
        
        # Get package path
        package_path = get_package_path(file_path)
        if not package_path:
            return line  # Can't convert, return as-is
        
        # Convert to absolute
        return f"{indent}from {package_path}.{module} import {imports}\n"
    
    # Match: from ..module import ...
    match = re.match(r'^(\s*)from\s+\.\.([^\s]+)\s+import\s+(.+)$', line)
    if match:
        indent = match.group(1)
        module = match.group(2)
        imports = match.group(3)
        
        # Get parent package path
        parts = file_path.parts
        if 'regimeflex' in parts:
            regimeflex_idx = parts.index('regimeflex')
            if len(parts) > regimeflex_idx + 2:  # Has parent
                subpath = '.'.join(parts[regimeflex_idx + 1:-2])  # Go up one level
                if subpath:
                    package_path = f"regimeflex.{subpath}"
                else:
                    package_path = "regimeflex"
            else:
                package_path = "regimeflex"
        else:
            return line  # Can't convert
        
        return f"{indent}from {package_path}.{module} import {imports}\n"
    
    # Match: from ...module import ... (two levels up)
    match = re.match(r'^(\s*)from\s+\.\.\.([^\s]+)\s+import\s+(.+)$', line)
    if match:
        indent = match.group(1)
        module = match.group(2)
        imports = match.group(3)
        
        # Get grandparent package path
        parts = file_path.parts
        if 'regimeflex' in parts:
            regimeflex_idx = parts.index('regimeflex')
            if len(parts) > regimeflex_idx + 3:  # Has grandparent
                subpath = '.'.join(parts[regimeflex_idx + 1:-3])  # Go up two levels
                if subpath:
                    package_path = f"regimeflex.{subpath}"
                else:
                    package_path = "regimeflex"
            else:
                package_path = "regimeflex"
        else:
            return line  # Can't convert
        
        return f"{indent}from {package_path}.{module} import {imports}\n"
    
    return line

def process_file(file_path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """Process a single file, converting relative imports."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0, 0
    
    converted = 0
    new_lines = []
    
    for line in lines:
        if re.match(r'^\s*from\s+\.', line):
            new_line = convert_relative_import(line, file_path)
            if new_line != line:
                converted += 1
                if dry_run:
                    print(f"  Would convert: {line.strip()}")
                    print(f"              -> {new_line.strip()}")
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    
    if not dry_run and converted > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return converted, 0
    
    return converted, len([l for l in lines if re.match(r'^\s*from\s+\.', l)])

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert relative imports to absolute imports')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--file', type=str, help='Process only a specific file')
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent
    regimeflex_dir = repo_root / 'regimeflex'
    
    if args.file:
        files = [Path(args.file)]
    else:
        files = list(regimeflex_dir.rglob('*.py'))
    
    total_converted = 0
    total_relative = 0
    
    for file_path in files:
        if '__pycache__' in str(file_path) or '.pyc' in str(file_path):
            continue
        
        converted, relative_count = process_file(file_path, dry_run=args.dry_run)
        total_converted += converted
        total_relative += relative_count
        
        if converted > 0:
            print(f"{'[DRY RUN] ' if args.dry_run else ''}{file_path}: {converted}/{relative_count} imports converted")
    
    print(f"\nTotal: {total_converted}/{total_relative} relative imports {'would be ' if args.dry_run else ''}converted")

if __name__ == '__main__':
    main()

