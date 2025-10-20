import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from engine.reconcile_positions import effective_positions_before
from engine.fills_state import FILLS_FILE

def setup_module(_):
    FILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if FILLS_FILE.exists():
        FILLS_FILE.unlink()
    FILLS_FILE.write_text("", encoding="utf-8")

def test_prefers_broker_snapshot_over_local_fills(tmp_path):
    # raw says 100, local fills would add +50, broker snapshot says 180 → expect 180
    FILLS_FILE.write_text(json.dumps({
        "ts":"2025-10-19T20:05:00Z","symbol":"QQQ","side":"buy",
        "qty":50,"status":"filled","filled_qty":50,"broker_id":"x"
    })+"\n", encoding="utf-8")
    raw = {"QQQ": 100.0}
    broker = {"QQQ": 180.0}
    eff, note = effective_positions_before(raw_positions_before=raw, broker_positions_snapshot=broker)
    assert note == "broker_snapshot"
    assert eff["QQQ"] == 180.0

def test_applies_local_partial_fills_when_no_broker():
    # start fresh file
    FILLS_FILE.write_text("", encoding="utf-8")
    FILLS_FILE.write_text(json.dumps({
        "ts":"2025-10-19T20:05:00Z","symbol":"QQQ","side":"buy",
        "qty":500,"status":"partially_filled","filled_qty":123,"broker_id":"y"
    })+"\n", encoding="utf-8")
    raw = {"QQQ": 100.0}
    eff, note = effective_positions_before(raw_positions_before=raw, broker_positions_snapshot=None)
    assert note == "local_fills_applied"
    assert eff["QQQ"] == 223.0  # 100 + 123
