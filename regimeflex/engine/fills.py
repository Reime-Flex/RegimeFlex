from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from .exec_planner import OrderIntent
from .positions import apply_fills
from .identity import RegimeFlexIdentity as RF

@dataclass(frozen=True)
class SimFill:
    symbol: str
    qty: float           # executed shares (positive)
    side: str            # "BUY" | "SELL"
    price: float         # executed price
    note: str

def simulate_fills(intents: List[OrderIntent], last_price: float) -> List[SimFill]:
    """
    Very simple simulator:
    - limit BUY → fills at min(limit, last_price)
    - limit SELL → fills at max(limit, last_price)
    - market/MOC → fills at last_price
    """
    fills: List[SimFill] = []
    for it in intents:
        px = last_price
        if it.order_type == "limit" and it.limit_price is not None:
            if it.side == "BUY":
                px = min(last_price, float(it.limit_price))
            else:
                px = max(last_price, float(it.limit_price))
            note = "limit simulated"
        elif it.order_type in ("market", "moc"):
            note = it.order_type + " simulated"
        else:
            note = "unknown type → market fallback"

        fills.append(SimFill(symbol=it.symbol, qty=float(it.qty), side=it.side, price=float(px), note=note))
    return fills

def fills_to_position_deltas(fills: List[SimFill]) -> Dict[str, float]:
    """
    BUY adds shares; SELL subtracts.
    """
    deltas: Dict[str, float] = {}
    for f in fills:
        signed = f.qty if f.side == "BUY" else -f.qty
        deltas[f.symbol] = deltas.get(f.symbol, 0.0) + signed
    return deltas

def apply_simulated_fills(current_positions: Dict[str, float], fills: List[SimFill]) -> Dict[str, float]:
    deltas = fills_to_position_deltas(fills)
    RF.print_log(f"Applying fills → deltas {deltas}", "INFO")
    return apply_fills(current_positions, deltas)
