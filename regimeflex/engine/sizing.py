# engine/sizing.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SizeConstraints:
    lot_size: int = 1
    min_qty: float = 1.0
    qty_precision: int = 0
    min_notional: float = 200.0

def load_constraints(cfg: dict) -> SizeConstraints:
    cons = (cfg.get("constraints") or {})
    return SizeConstraints(
        lot_size=int(cons.get("lot_size", 1)),
        min_qty=float(cons.get("min_qty", 1.0)),
        qty_precision=int(cons.get("qty_precision", 0)),
        min_notional=float(cons.get("min_notional", 200.0)),
    )

def round_qty(qty: float, lot_size: int, precision: int) -> float:
    """
    - Snap to lot_size multiples
    - Then round to precision decimals
    """
    if lot_size <= 0:
        lot_size = 1
    # snap to lot
    snapped = (qty // lot_size) * lot_size
    # precision (for fractional shares use precision>0, lot_size usually 1)
    factor = 10 ** max(0, precision)
    return round(snapped * 1.0, precision) if precision > 0 else float(int(snapped))

def sanitize_desired_qty(desired_shares: float, price: float, constraints: SizeConstraints):
    """
    Returns (adj_qty, note). adj_qty may be 0 if below thresholds.
    """
    q = max(0.0, float(desired_shares))
    q_rounded = round_qty(q, constraints.lot_size, constraints.qty_precision)

    note_parts = []
    if abs(q_rounded - q) > 1e-9:
        note_parts.append(f"rounded {q:.4f}→{q_rounded:.4f}")

    # enforce min_qty after rounding
    if q_rounded < constraints.min_qty:
        return 0.0, "below min_qty"

    # enforce min_notional
    if q_rounded * float(price) < constraints.min_notional:
        return 0.0, "below min_notional"

    note = " | ".join(note_parts) if note_parts else "OK"
    return q_rounded, note
