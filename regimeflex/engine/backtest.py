from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
import numpy as np

from .signals import detect_regime, trend_signal, mr_signal, RegimeState
from .risk import RiskConfig, RiskInputs, circuit_breakers, dynamic_position_size

def _slip(px: float, side: str, bps: float) -> float:
    """
    Applies slippage in basis points:
      BUY  → pay higher:  px * (1 + bps/1e4)
      SELL → receive less: px * (1 - bps/1e4)
    """
    m = (bps / 1e4)
    return px * (1 + m) if side.upper() == "BUY" else px * (1 - m)

@dataclass(frozen=True)
class BTConfig:
    start_cash: float = 25_000.0
    vix_assumption: float | None = None     # None = ignore VIX, else constant
    min_trade_value: float = 200.0          # ignore dust
    risk: RiskConfig = RiskConfig()
    # NEW: frictions
    commission_per_share: float = 0.0     # e.g., 0.005
    fixed_fee_per_trade: float = 0.0      # e.g., 0.00
    slippage_bps: float = 10.0            # 10 bps = 0.10%

@dataclass(frozen=True)
class BTResult:
    equity_curve: pd.Series
    trades: int
    cagr: float
    max_dd: float
    sharpe: float

def _metrics(equity: pd.Series) -> tuple[float, float, float]:
    if len(equity) == 0:
        return 0.0, 0.0, 0.0
    
    rets = equity.pct_change().fillna(0.0)
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / max(yrs, 1e-9)) - 1
    peak = equity.cummax()
    dd = (equity / peak - 1.0).min()
    sharpe = (rets.mean() / (rets.std(ddof=0) + 1e-12)) * np.sqrt(252) if rets.std(ddof=0) > 0 else 0.0
    return float(cagr), float(abs(dd)), float(sharpe)

def run_backtest(qqq: pd.DataFrame, psq: pd.DataFrame, cfg: BTConfig) -> BTResult:
    # align dates
    idx = qqq.index.intersection(psq.index)
    qqq = qqq.loc[idx].copy()
    psq = psq.loc[idx].copy()

    cash = cfg.start_cash
    shares = 0.0
    symbol = None
    trades = 0

    equity = []
    dates = []

    # step through days, use info up to day t (no lookahead)
    warmup = min(60, len(idx) - 10)  # ensure we have at least 10 days to process
    for i in range(warmup, len(idx)):
        d = idx[i]
        q_hist = qqq.iloc[: i + 1]
        p_hist = psq.iloc[: i + 1]

        # 1) regime & signals using history up to today
        regime0 = detect_regime(q_hist["close"])
        regime = RegimeState(bull=regime0.bull, vix=cfg.vix_assumption, qqq_rvol_20=regime0.qqq_rvol_20)
        t_sig = trend_signal(q_hist, regime)
        act_df = q_hist if regime.bull else p_hist
        m_sig = mr_signal(act_df, regime)

        # choose direction
        if t_sig.entry and not t_sig.exit:
            core_dir = "LONG"
        else:
            core_dir = "FLAT"

        if core_dir == "LONG":
            direction = "LONG"
            sym = "QQQ"
            df = q_hist
        else:
            # allow MR short via PSQ only if entry
            if (not regime.bull) and m_sig.entry and m_sig.direction == "SHORT":
                direction = "SHORT"
                sym = "PSQ"  # long PSQ approximates short QQQ
                df = p_hist
            elif regime.bull and m_sig.entry and m_sig.direction == "LONG":
                direction = "LONG"
                sym = "QQQ"
                df = q_hist
            else:
                direction = "FLAT"
                sym = None
                df = None

        # 2) sizing & blockers
        if direction == "FLAT":
            target_dollars = 0.0
        else:
            price = float(df["close"].iloc[-1])
            rin = RiskInputs(
                equity=cash + shares * (qqq["close"].iloc[i] if symbol == "QQQ" else psq["close"].iloc[i] if symbol else 0.0),
                price=price,
                vix=cfg.vix_assumption,
                qqq_close=q_hist["close"],
                is_fomc_window=False,
                is_opex=False,
            )
            blocked, _ = circuit_breakers(rin, cfg.risk)
            if blocked:
                target_dollars = 0.0
            else:
                target_dollars, _ = dynamic_position_size(rin, df["close"], df["high"], df["low"], cfg.risk)

        # 3) rebalance if above threshold
        # compute current position market value
        curr_price = float(qqq["close"].iloc[i] if symbol == "QQQ" else psq["close"].iloc[i] if symbol else 0.0)
        curr_value = shares * curr_price
        delta = target_dollars - curr_value

        if abs(delta) >= cfg.min_trade_value:
            # If we're changing symbols, first fully liquidate existing exposure
            if sym != symbol and symbol is not None:
                # SELL all current shares of old symbol (side = SELL)
                side = "SELL"
                exec_px = float(qqq["close"].iloc[i] if symbol == "QQQ" else psq["close"].iloc[i])
                exec_px = _slip(exec_px, side, cfg.slippage_bps)
                commission = abs(shares) * cfg.commission_per_share
                fee = cfg.fixed_fee_per_trade
                cash += shares * exec_px - commission - fee
                shares = 0.0
                symbol = None
                trades += 1
                curr_price = 0.0
                curr_value = 0.0

            if target_dollars == 0.0:
                if symbol is not None and abs(curr_value) >= cfg.min_trade_value:
                    # go flat: SELL all
                    side = "SELL"
                    exec_px = float(qqq["close"].iloc[i] if symbol == "QQQ" else psq["close"].iloc[i])
                    exec_px = _slip(exec_px, side, cfg.slippage_bps)
                    commission = abs(shares) * cfg.commission_per_share
                    fee = cfg.fixed_fee_per_trade
                    cash += shares * exec_px - commission - fee
                    shares = 0.0
                    symbol = None
                    trades += 1
            else:
                # open/resize to target dollars on (sym)
                px = float(qqq["close"].iloc[i] if sym == "QQQ" else psq["close"].iloc[i])
                new_shares = target_dollars / px
                delta_shares = new_shares - (shares if symbol == sym else 0.0)

                if abs(delta_shares) * px >= cfg.min_trade_value:
                    side = "BUY" if delta_shares > 0 else "SELL"
                    exec_px = _slip(px, side, cfg.slippage_bps)
                    commission = abs(delta_shares) * cfg.commission_per_share
                    fee = cfg.fixed_fee_per_trade
                    # adjust cash by the delta trade, include costs
                    cash -= delta_shares * exec_px + commission + fee
                    # update position to new target
                    shares = new_shares
                    symbol = sym
                    trades += 1

        # 4) mark-to-market equity
        mtm_price = float(qqq["close"].iloc[i] if symbol == "QQQ" else psq["close"].iloc[i] if symbol else 0.0)
        eq = cash + shares * mtm_price
        dates.append(d)
        equity.append(eq)

    eq_series = pd.Series(equity, index=pd.DatetimeIndex(dates, name="date"))
    cagr, maxdd, sharpe = _metrics(eq_series)
    return BTResult(eq_series, trades, cagr, maxdd, sharpe)
