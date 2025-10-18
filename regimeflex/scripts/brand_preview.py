import json
import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF

def show_palette():
    palette_path = Path("branding/color-palette.json")
    data = json.loads(palette_path.read_text())
    RF.print_log("Color Palette (ENS-inspired):", "INFO")
    for name, hexcode in data.items():
        RF.print_log(f"{name:>14}: {hexcode}", "SUCCESS")

def show_sample_logs():
    RF.print_log("Initializing design system", "INFO")
    RF.print_log("Trend signal generated: QQQ LONG 25%", "SIGNAL")
    RF.print_log("Volatility rising: tighten risk budget", "RISK")
    RF.print_log("Data fetch failed: retrying…", "ERROR")
    RF.print_log("Heartbeat OK; telemetry online", "SUCCESS")

if __name__ == "__main__":
    show_palette()
    print()
    show_sample_logs()
