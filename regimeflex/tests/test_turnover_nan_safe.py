import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from engine.turnover import enforce_turnover_cap
from engine.exposure_delta import current_exposure_weights, exposure_delta

def test_turnover_zero_when_alloc_equals_current_and_short_price_nan():
    # Execution pair QQQ/PSQ
    positions_before = {"QQQ": 497.0, "PSQ": 0.0}
    prices = {"QQQ": 400.0, "PSQ": float("nan")}  # PSQ price missing today
    # Equity_now from positions (gross): 497 * 400 = 198800
    equity_now = abs(positions_before["QQQ"] * prices["QQQ"])
    sides = ["QQQ","PSQ"]

    prev_w = current_exposure_weights(positions_before, prices, equity_now, sides)
    # target wants 100% QQQ, 0% PSQ — which is already true in prev_w within rounding
    desired = {"QQQ": prev_w["QQQ"], "PSQ": 0.0}

    # Enforce turnover with NaN-proof logic → turnover should be 0, alloc unchanged
    new_w, desired_mv, frac, note = enforce_turnover_cap(
        alloc_weights=desired,
        positions_before=positions_before,
        last_prices=prices,
        equity=equity_now,
        max_turnover_frac=0.15,
        mode="clamp",
    )
    assert frac == 0.0
    assert note == "OK"
    # deltas should be ~0
    dW = exposure_delta(prev_w, new_w, sides)
    assert abs(dW["QQQ"]) < 1e-9 and abs(dW["PSQ"]) < 1e-9

def test_turnover_clamps_when_over_cap():
    positions_before = {"QQQ": 0.0, "PSQ": 0.0}
    prices = {"QQQ": 100.0, "PSQ": 100.0}
    equity_now = 100000.0
    desired = {"QQQ": 1.0, "PSQ": 0.0}  # wants to buy $100k QQQ
    new_w, desired_mv, frac, note = enforce_turnover_cap(
        alloc_weights=desired,
        positions_before=positions_before,
        last_prices=prices,
        equity=equity_now,
        max_turnover_frac=0.05,  # 5%
        mode="clamp",
    )
    # turnover (100%) > 5% → clamped
    assert frac == 1.0
    assert "clamp×" in note
    # new_w should be ~5% not 100%
    assert 0.049 <= new_w["QQQ"] <= 0.051
