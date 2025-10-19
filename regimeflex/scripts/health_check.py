import sys
import json
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.health import run_health
from engine.identity import RegimeFlexIdentity as RF

if __name__ == "__main__":
    rep = run_health()
    # pretty print
    print(json.dumps({
        "status": rep.status,
        "timestamp": rep.timestamp,
        "checks": [c.__dict__ for c in rep.checks]
    }, indent=2))
    # non-zero exit on FAIL
    if rep.status == "FAIL":
        RF.print_log("Health check failed.", "ERROR")
        sys.exit(1)
    elif rep.status == "WARN":
        RF.print_log("Health check warnings present.", "RISK")
        sys.exit(0)
    else:
        sys.exit(0)
