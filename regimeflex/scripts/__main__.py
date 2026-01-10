"""
Module entrypoint for regimeflex.scripts

Allows execution of scripts via: python -m regimeflex.scripts.<script_name>

This ensures proper package context so all relative imports work correctly.
"""

import sys
import importlib.util
from pathlib import Path

def main():
    """Main entrypoint for scripts module."""
    if len(sys.argv) < 2:
        print("Usage: python -m regimeflex.scripts <script_name>")
        print("\nAvailable scripts:")
        scripts_dir = Path(__file__).parent
        for script_file in sorted(scripts_dir.glob("*.py")):
            if script_file.name != "__main__.py" and script_file.name != "__init__.py":
                print(f"  {script_file.stem}")
        sys.exit(1)
    
    script_name = sys.argv[1]
    script_path = Path(__file__).parent / f"{script_name}.py"
    
    if not script_path.exists():
        print(f"Error: Script '{script_name}' not found")
        sys.exit(1)
    
    # Load and execute the script as a module
    spec = importlib.util.spec_from_file_location(f"regimeflex.scripts.{script_name}", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"regimeflex.scripts.{script_name}"] = module
    spec.loader.exec_module(module)
    
    if hasattr(module, "main"):
        sys.exit(module.main() or 0)
    else:
        print(f"Error: {script_name}.py does not have a main() function")
        sys.exit(1)

if __name__ == "__main__":
    main()

