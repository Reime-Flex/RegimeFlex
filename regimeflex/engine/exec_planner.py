from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

from regimeflex.engine.portfolio import TargetExposure
from regimeflex.engine.config import Config
from regimeflex.engine.sizing import load_constraints, sanitize_desired_qty
from regimeflex.engine.identity import RegimeFlexIdentity as RF

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

def _get_slippage_buffer() -> float:
    """
    Get slippage buffer from safety config.
    Default 0.05% (0.0005) for execution certainty on volatile ETFs like TQQQ.
    """
    try:
        from regimeflex.engine.safety_wrapper import get_safety_config
        cfg = get_safety_config()
        return cfg.slippage_buffer_pct
    except Exception:
        return 0.0005  # Default 0.05%

from regimeflex.engine.indicators import atr

def calculate_adaptive_limit_offset(
    df: pd.DataFrame,
    base_offset_pct: float = 0.005,  # 0.5% base
    atr_multiplier: float = 0.3,
    max_offset_pct: float = 0.02  # Cap at 2%
) -> float:
    """
    Calculate adaptive limit price offset based on recent volatility.
    Higher ATR = wider offset to improve fill probability.
    """
    if len(df) < 14:
        return base_offset_pct
    
    # Calculate ATR safely
    try:
        current_atr = atr(df["high"], df["low"], df["close"], n=14).iloc[-1]
        current_price = df["close"].iloc[-1]
        
        if pd.isna(current_atr) or current_price <= 0:
            return base_offset_pct
        
        # ATR as percentage of price
        atr_pct = float(current_atr) / float(current_price)
        
        # Adaptive offset: base + (atr_pct * multiplier)
        adaptive_offset = base_offset_pct + (atr_pct * atr_multiplier)
        
        return min(adaptive_offset, max_offset_pct)
    except Exception:
        return base_offset_pct

def plan_orders(
    current_positions: Dict[str, float],
    target: TargetExposure,
    current_price: float,
    minutes_to_close: int,
    min_trade_value: float = 200.0,
    emergency_override: bool = False,
    price_df: pd.DataFrame | None = None,
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
        
        # Calculate adaptive offset
        if price_df is not None and len(price_df) >= 14:
            offset = calculate_adaptive_limit_offset(price_df)
        else:
            offset = 0.005  # Fallback to 0.5%
        
        # Price improvement/offset anchor
        if delta > 0:
            limit_price = round(current_price * (1 - offset), 2)
        else:
            limit_price = round(current_price * (1 + offset), 2)

    side = "BUY" if delta > 0 else "SELL"
    
    # Sanitize quantity against broker constraints
    from regimeflex.config.paths import PROJECT_ROOT
    broker_cfg = Config(PROJECT_ROOT)._load_yaml("config/broker.yaml") if (Config(PROJECT_ROOT).root / "config/broker.yaml").exists() else {}
    cons = load_constraints(broker_cfg)
    raw_qty = abs(delta)
    adj_qty, size_note = sanitize_desired_qty(raw_qty, current_price, cons)

    if adj_qty <= 0.0:
        RF.print_log(f"Skipped trade for {sym}: {size_note}", "INFO")
        return intents  # empty

    qty = adj_qty

    intent = OrderIntent(
        symbol=sym,
        side=side,
        qty=qty,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        reason=f"plan_orders: curr={current_shares:.2f}, desired={desired_shares:.2f}, "
               f"delta={delta:.2f} | sizing={size_note}"
    )
    intents.append(intent)
    return intents
