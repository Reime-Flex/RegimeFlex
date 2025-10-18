from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict

STATE_DIR = Path("data/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
POS_PATH = STATE_DIR / "positions.json"

@dataclass(frozen=True)
class Position:
    symbol: str
    shares: float  # signed; positive long, negative short (we'll use >=0 for ETFs)

def load_positions() -> Dict[str, float]:
    """Return {SYMBOL: shares} from the local state file, or empty dict."""
    if not POS_PATH.exists():
        return {}
    try:
        data = json.loads(POS_PATH.read_text())
        # normalize symbols to upper case floats
        return {str(k).upper(): float(v) for k, v in data.items()}
    except Exception:
        # if corrupted, fall back cleanly
        return {}

def save_positions(positions: Dict[str, float]) -> None:
    """Atomically write positions to disk."""
    tmp = POS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({k.upper(): float(v) for k, v in positions.items()}, ensure_ascii=False, indent=2))
    tmp.replace(POS_PATH)

def set_position(symbol: str, shares: float) -> Dict[str, float]:
    """Convenience helper to update one symbol and persist."""
    symbol = symbol.upper()
    positions = load_positions()
    if abs(shares) < 1e-9:
        positions.pop(symbol, None)
    else:
        positions[symbol] = float(shares)
    save_positions(positions)
    return positions

def apply_fills(positions: Dict[str, float], fills: Dict[str, float]) -> Dict[str, float]:
    """
    Apply executed fills to positions.
    `fills` is {SYMBOL: delta_shares_signed}
    """
    out = {k.upper(): float(v) for k, v in positions.items()}
    for sym, dsh in fills.items():
        sym = sym.upper()
        out[sym] = float(out.get(sym, 0.0) + float(dsh))
        if abs(out[sym]) < 1e-9:
            out.pop(sym, None)
    save_positions(out)
    return out
