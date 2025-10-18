from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

from .portfolio import TargetExposure

@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str              # "BUY" | "SELL"
    qty: float             # positive shares
    order_type: str        # "limit" | "market" | "moc"
    time_in_force: str     # "day" | "cls"
    limit_price: float | None
    reason: str

def _normalize_target_shares_for_symbol(target: TargetExposure) -> float:
    """
    For PSQ (inverse ETF), our 'short' QQQ bias is expressed by going LONG PSQ.
    So we treat desired shares as ABS() for PSQ.
    For QQQ, signed shares are used directly (LONG positive; FLAT is zero).
    """
    if target.symbol.upper() == "PSQ":
        return abs(target.shares)
    return target.shares

def plan_orders(
    current_positions: Dict[str, float],
    target: TargetExposure,
    current_price: float,
    minutes_to_close: int,
    min_trade_value: float = 200.0,
    emergency_override: bool = False
) -> List[OrderIntent]:
    """
    Convert a target exposure into a list of order intents.

    - Skips tiny changes below min_trade_value.
    - Chooses MOC if within 30 minutes of close; else limit (or market if emergency).
    - For PSQ, uses absolute shares (we do not short PSQ).
    """
    intents: List[OrderIntent] = []

    sym = target.symbol.upper()
    current_shares = float(current_positions.get(sym, 0.0))

    # Normalize target shares
    desired_shares = _normalize_target_shares_for_symbol(target)

    # Compute delta in shares (positive => need to BUY more)
    delta = desired_shares - current_shares

    # If target is FLAT, desired_shares should be 0 already
    if target.direction == "FLAT":
        desired_shares = 0.0
        delta = -current_shares  # close any residual

    # Avoid dust
    if abs(delta) * current_price < min_trade_value:
        return intents  # empty means "no trade"

    # Order type logic
    if minutes_to_close <= 30:
        order_type = "moc"
        tif = "cls"
        limit_price = None
    else:
        order_type = "market" if emergency_override else "limit"
        tif = "day"
        # Price improvement anchor: buy slightly below, sell slightly above
        if delta > 0:
            limit_price = round(current_price * 0.995, 2)
        else:
            limit_price = round(current_price * 1.005, 2)

    side = "BUY" if delta > 0 else "SELL"
    qty = abs(delta)

    intent = OrderIntent(
        symbol=sym,
        side=side,
        qty=qty,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        reason=f"plan_orders: curr={current_shares:.2f}, desired={desired_shares:.2f}, delta={delta:.2f}"
    )
    intents.append(intent)
    return intents
