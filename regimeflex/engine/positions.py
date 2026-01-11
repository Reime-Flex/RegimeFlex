from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict

from regimeflex.config.paths import POSITIONS_FILE as POS_PATH
from regimeflex.utils.atomic_file import atomic_write_json, atomic_read_json

@dataclass(frozen=True)
class Position:
    symbol: str
    shares: float  # signed; positive long, negative short (we'll use >=0 for ETFs)

def load_positions() -> Dict[str, float]:
    """Return {SYMBOL: shares} from the local state file, or empty dict."""
    # Use atomic read to prevent reading corrupted files
    data = atomic_read_json(POS_PATH, default={})
    if not data:
        return {}
    try:
        # normalize symbols to upper case floats
        return {str(k).upper(): float(v) for k, v in data.items()}
    except Exception:
        # if corrupted, fall back cleanly
        return {}

def save_positions(positions: Dict[str, float]) -> None:
    """Atomically write positions to disk with file locking."""
    # Normalize positions (upper case keys, float values)
    normalized = {k.upper(): float(v) for k, v in positions.items()}
    # Use atomic write utility (includes temp file + rename + locking)
    success = atomic_write_json(POS_PATH, normalized, indent=2, ensure_ascii=False)
    if not success:
        # Log error but don't raise (caller should handle)
        import sys
        print(f"Warning: Failed to save positions to {POS_PATH}", file=sys.stderr)

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
