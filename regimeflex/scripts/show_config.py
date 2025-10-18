import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
import pprint

if __name__ == "__main__":
    RF.print_log("Loading RegimeFlex configuration…", "INFO")
    cfg = Config(".")
    RF.print_log("Strategies:", "INFO")
    pprint.pprint(cfg.strategies)
    RF.print_log("Risk:", "INFO")
    pprint.pprint(cfg.risk)
    RF.print_log("Schedule:", "INFO")
    pprint.pprint(cfg.schedule)
    RF.print_log("Config load OK ✅", "SUCCESS")
