# engine/plan_coalesce.py
from __future__ import annotations
from typing import Dict, List, Tuple

def coalesce_side_flip(
    positions_before: Dict[str, float],     # {"QQQ": shares, "PSQ": shares}
    target_weights: Dict[str, float],       # {"QQQ": w, "PSQ": w} AFTER caps/turnover
    prices: Dict[str, float],               # {"QQQ": px, "PSQ": px} (common date)
    equity: float,
    long_sym: str,
    short_sym: str,
    close_dust_shares: float = 1.0,
    min_open_notional: float = 200.0,
    prefer_single_leg_if_net_small: bool = True,
) -> Tuple[List[Dict], str]:
    """
    Returns (intents, note).
    Intents are dicts with symbol, side, qty, reason (planner will fill type/TIF).
    Only handles side flip coalescing; if not a flip, returns [] with 'no_flip'.
    """
    long_pos  = float(positions_before.get(long_sym, 0.0))
    short_pos = float(positions_before.get(short_sym, 0.0))
    long_px   = float(prices.get(long_sym, 0.0))
    short_px  = float(prices.get(short_sym, 0.0))
    w_long    = float(target_weights.get(long_sym, 0.0))
    w_short   = float(target_weights.get(short_sym, 0.0))

    # target shares
    tgt_long_sh  = (equity * w_long)  / long_px if long_px  > 0 else 0.0
    tgt_short_sh = (equity * w_short) / short_px if short_px > 0 else 0.0

    # Detect flips (we only hold one side by design; a flip means current side>0 and target other_side>0)
    flip_to_long  = (short_pos > 0.0) and (tgt_long_sh  > 0.0) and (w_short <= 1e-9)
    flip_to_short = (long_pos  > 0.0) and (tgt_short_sh > 0.0) and (w_long  <= 1e-9)
    if not (flip_to_long or flip_to_short):
        return [], "no_flip"

    intents: List[Dict] = []
    if flip_to_long:
        # default: close short, then open long
        close_qty = short_pos
        open_qty  = max(0.0, tgt_long_sh)
        # Dust rule on close
        if close_qty < close_dust_shares:
            close_qty = 0.0
        # Notional rule on open
        if open_qty * long_px < min_open_notional:
            open_qty = 0.0
        # single-leg preference if they nearly cancel out (rare with 1x ETFs, but safe)
        if prefer_single_leg_if_net_small and close_qty > 0.0 and open_qty > 0.0:
            # compare notionals; keep only larger leg if the smaller < min_open_notional
            if min(close_qty * short_px, open_qty * long_px) < min_open_notional:
                # drop the small one
                if close_qty * short_px >= open_qty * long_px:
                    open_qty = 0.0
                else:
                    close_qty = 0.0

        if close_qty > 0.0:
            intents.append({"symbol": short_sym, "side": "sell", "qty": round(close_qty, 6),
                            "reason": "coalesce: close_old_side"})
        if open_qty > 0.0:
            intents.append({"symbol": long_sym, "side": "buy", "qty": round(open_qty, 6),
                            "reason": "coalesce: open_new_side"})

        return intents, "flip_to_long"

    if flip_to_short:
        close_qty = long_pos
        open_qty  = max(0.0, tgt_short_sh)
        if close_qty < close_dust_shares:
            close_qty = 0.0
        if open_qty * short_px < min_open_notional:
            open_qty = 0.0
        if prefer_single_leg_if_net_small and close_qty > 0.0 and open_qty > 0.0:
            if min(close_qty * long_px, open_qty * short_px) < min_open_notional:
                if close_qty * long_px >= open_qty * short_px:
                    open_qty = 0.0
                else:
                    close_qty = 0.0

        if close_qty > 0.0:
            intents.append({"symbol": long_sym, "side": "sell", "qty": round(close_qty, 6),
                            "reason": "coalesce: close_old_side"})
        if open_qty > 0.0:
            intents.append({"symbol": short_sym, "side": "buy", "qty": round(open_qty, 6),
                            "reason": "coalesce: open_new_side"})

        return intents, "flip_to_short"

    return [], "no_flip"
