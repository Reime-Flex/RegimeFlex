from __future__ import annotations
from dataclasses import dataclass

import pandas as pd

from .signals import detect_regime, trend_signal, mr_signal, RegimeState
from .risk import RiskConfig, RiskInputs, circuit_breakers, dynamic_position_size

@dataclass(frozen=True)
class TargetExposure:
    symbol: str
    direction: str         # "LONG", "SHORT", or "FLAT"
    dollars: float         # desired notional in $
    shares: float          # desired shares (signed for direction)
    notes: str

def choose_active_symbol(regime: RegimeState, bull_symbol="QQQ", bear_symbol="PSQ") -> str:
    return bull_symbol if regime.bull else bear_symbol

def combine_signals(trend_entry: bool, trend_exit: bool, mr_dir: str, mr_entry: bool) -> str:
    """
    Priority: Trend defines core bias (LONG or FLAT).
    MR overlays only if aligned with trend bias in bull regime,
    or provides short bias in bear regime via PSQ.
    Output: "LONG" | "SHORT" | "FLAT"
    """
    # Trend bias
    trend_bias = "LONG" if trend_entry and not trend_exit else "FLAT"

    if trend_bias == "LONG":
        # allow MR to confirm long only
        if mr_entry and mr_dir == "LONG":
            return "LONG"
        return "LONG"  # trend alone ok
    else:
        # No long trend; in bear regime MR may short (via PSQ)
        if mr_entry and mr_dir == "SHORT":
            return "SHORT"
        return "FLAT"

def compute_target_exposure(
    qqq: pd.DataFrame,
    psq: pd.DataFrame,
    equity: float,
    vix: float | None = None,
    cfg: RiskConfig | None = None,
    is_fomc_window: bool = False,
    is_opex_day: bool = False,
) -> TargetExposure:
    cfg = cfg or RiskConfig()

    # 1) Regime
    regime = detect_regime(qqq["close"])
    regime = RegimeState(bull=regime.bull, vix=vix, qqq_rvol_20=regime.qqq_rvol_20)

    # 2) Signals
    t_sig = trend_signal(qqq, regime, vix_max=30.0, qqq_vol_50d_max=0.40)
    active_df = qqq if regime.bull else psq
    m_sig = mr_signal(active_df, regime, z_len=20, vol_confirm_mult=1.2)

    # 3) Direction decision
    direction = combine_signals(t_sig.entry, t_sig.exit, m_sig.direction, m_sig.entry)
    symbol = "QQQ" if regime.bull else "PSQ"
    df = active_df

    # 4) Circuit breakers & sizing (QQQ close drives risk)
    inputs = RiskInputs(
        equity=float(equity),
        price=float(df["close"].iloc[-1]),
        vix=vix,
        qqq_close=qqq["close"],
        is_fomc_window=is_fomc_window,
        is_opex=is_opex_day,
    )
    blocked, reason = circuit_breakers(inputs, cfg)
    if blocked or direction == "FLAT":
        return TargetExposure(symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
                              notes=f"{'BLOCKED: ' + reason if blocked else 'Direction FLAT'} | "
                                    f"trend(entry={t_sig.entry}, exit={t_sig.exit}), mr({m_sig.direction}, entry={m_sig.entry})")

    dollars, note = dynamic_position_size(inputs, df["close"], df["high"], df["low"], cfg)
    if dollars <= 0:
        return TargetExposure(symbol=symbol, direction="FLAT", dollars=0.0, shares=0.0,
                              notes=f"Zero size | {note}")

    # 5) Shares (signed)
    sign = 1 if direction == "LONG" else -1
    shares = sign * (dollars / inputs.price)

    return TargetExposure(symbol=symbol, direction=direction, dollars=dollars, shares=shares,
                          notes=f"{note} | regime={'BULL' if regime.bull else 'BEAR'}; "
                                f"trend(entry={t_sig.entry}, exit={t_sig.exit}); "
                                f"mr(dir={m_sig.direction}, entry={m_sig.entry}, z={m_sig.z})")
