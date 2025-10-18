import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.data import get_daily_bars
from engine.indicators import sma, atr, zscore

def test_indicators_shapes():
    df = get_daily_bars("QQQ")
    s20 = sma(df["close"], 20)
    a14 = atr(df["high"], df["low"], df["close"], 14)
    z20 = zscore(df["close"], 20)

    # Shapes match input
    assert len(s20) == len(df)
    assert len(a14) == len(df)
    assert len(z20) == len(df)

def test_indicators_non_null_after_warmup():
    df = get_daily_bars("QQQ")
    s20 = sma(df["close"], 20).dropna()
    a14 = atr(df["high"], df["low"], df["close"], 14).dropna()
    z20 = zscore(df["close"], 20).dropna()

    assert len(s20) > 0
    assert len(a14) > 0
    assert len(z20) > 0
