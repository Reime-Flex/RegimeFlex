import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.killswitch import enable, disable, is_killed

if __name__ == "__main__":
    if is_killed():
        disable()
        RF.print_log("Kill-switch DISABLED", "SUCCESS")
    else:
        enable()
        RF.print_log("Kill-switch ENABLED", "RISK")
