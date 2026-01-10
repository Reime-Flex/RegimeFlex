"""
RegimeFlex Package Entrypoint

This allows RegimeFlex to be executed as a Python module:
    python -m regimeflex [command] [args...]

This ensures proper package context and resolves all relative imports correctly.
"""

import sys
import os
from pathlib import Path

# Ensure we're running from the correct context
# When run as 'python -m regimeflex', Python sets __package__ correctly
# and all relative imports will work

def main():
    """Main entrypoint for module execution."""
    if len(sys.argv) < 2:
        print("RegimeFlex - Automated TQQQ/SQQQ Swing Trading System")
        print("\nUsage:")
        print("  python -m regimeflex run          # Run daily trading cycle")
        print("  python -m regimeflex http         # Start HTTP trigger server")
        print("  python -m regimeflex health        # Run health check")
        print("  python -m regimeflex <script>     # Run a script from scripts/")
        print("\nFor more options, see:")
        print("  python -m regimeflex --help")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--help" or command == "-h":
        print("RegimeFlex Module Entrypoint")
        print("\nCommands:")
        print("  run              Run daily trading cycle (offline)")
        print("  http             Start HTTP trigger server (for Railway/cron)")
        print("  health           Run full health check")
        print("  <script_name>    Run a script from regimeflex/scripts/")
        print("\nExamples:")
        print("  python -m regimeflex run")
        print("  python -m regimeflex http")
        print("  python -m regimeflex run_offline_from_config")
        sys.exit(0)
    
    # Route to appropriate handler
    if command == "run":
        from engine.runner import run_daily_offline
        from engine.config import Config
        
        cfg = Config(".")
        run = cfg.run or {}
        result = run_daily_offline(
            equity=float(run.get("equity", 25000)),
            vix=run.get("vix_assumption", 20.0),
            minutes_to_close=int(run.get("minutes_to_close", 28)),
            min_trade_value=float(run.get("min_trade_value", 200.0))
        )
        print(f"Run completed: {result}")
        sys.exit(0)
    
    elif command == "http":
        # Start HTTP server
        from scripts.run_http_trigger import main
        
        main()
        sys.exit(0)
    
    elif command == "health":
        from engine.health import run_health
        
        rep = run_health()
        print(f"Health Status: {rep.status}")
        for check in rep.checks:
            print(f"  {check.name}: {check.status}")
        sys.exit(0 if rep.status == "PASS" else 1)
    
    else:
        # Try to run as a script name
        script_path = Path(__file__).parent / "scripts" / f"{command}.py"
        if script_path.exists():
            # Import and run the script's main function
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"scripts.{command}", script_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"scripts.{command}"] = module
            spec.loader.exec_module(module)
            
            if hasattr(module, "main"):
                sys.exit(module.main() or 0)
            else:
                print(f"Error: {command}.py does not have a main() function")
                sys.exit(1)
        else:
            print(f"Error: Unknown command '{command}'")
            print("Run 'python -m regimeflex --help' for usage")
            sys.exit(1)


if __name__ == "__main__":
    main()

