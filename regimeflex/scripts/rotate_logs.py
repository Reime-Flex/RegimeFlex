import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.logrotate import rotate_all

if __name__ == "__main__":
    RF.print_log("Starting log rotation…", "INFO")
    res = rotate_all()
    RF.print_log(f"Done. {res}", "SUCCESS")
