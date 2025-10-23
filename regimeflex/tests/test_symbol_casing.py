from engine.symnorm import map_keys_upper
from engine.exposure_delta import current_exposure_weights

def test_uppercase_alignment_prevents_zero_prev_w():
    positions = {"qqq": 10.0, "PsQ": 0.0}
    prices = {"QQQ": 100.0, "PSQ": 90.0}
    positions = map_keys_upper(positions)
    sides = ["QQQ", "PSQ"]
    equity_now = positions["QQQ"] * prices["QQQ"]  # 1000
    prev = current_exposure_weights(positions, prices, equity_now, sides)
    # weight for QQQ should be 1.0, not 0.0
    assert abs(prev["QQQ"] - 1.0) < 1e-9
