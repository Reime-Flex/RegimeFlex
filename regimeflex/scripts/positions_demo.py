import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.positions import load_positions, save_positions, set_position, apply_fills

if __name__ == "__main__":
    RF.print_log("Loading existing positions…", "INFO")
    pos = load_positions()
    RF.print_log(f"Current: {pos}", "INFO")

    RF.print_log("Setting QQQ to 10.0 shares…", "INFO")
    pos = set_position("QQQ", 10.0)
    RF.print_log(f"Now: {pos}", "SUCCESS")

    RF.print_log("Applying fills: +5 QQQ, +12 PSQ…", "INFO")
    pos = apply_fills(pos, {"QQQ": 5.0, "PSQ": 12.0})
    RF.print_log(f"Now: {pos}", "SUCCESS")

    RF.print_log("Zeroing PSQ (will be removed)…", "INFO")
    pos = set_position("PSQ", 0.0)
    RF.print_log(f"Final: {pos}", "SUCCESS")

    RF.print_log("Positions store OK ✅ (see data/state/positions.json)", "SUCCESS")
