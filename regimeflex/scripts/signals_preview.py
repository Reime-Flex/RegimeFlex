import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.data import get_daily_bars
from engine.signals import detect_regime, trend_signal, mr_signal, RegimeState

if __name__ == "__main__":
    # Load cached mock data (from Step 5 seeder)
    qqq = get_daily_bars("QQQ")
    psq = get_daily_bars("PSQ")

    # Detect regime from QQQ
    regime = detect_regime(qqq["close"])
    # Mock VIX and override regime vol if you want:
    regime = RegimeState(bull=regime.bull, vix=18.0, qqq_rvol_20=regime.qqq_rvol_20)

    RF.print_log(f"Regime → bull={regime.bull}, vix={regime.vix}, rvol20≈{regime.qqq_rvol_20:.2f}", "INFO")

    # Trend engine on QQQ
    t_sig = trend_signal(qqq, regime, vix_max=30.0, qqq_vol_50d_max=0.40)
    RF.print_log(f"Trend: entry={t_sig.entry}, exit={t_sig.exit}, reason={t_sig.reason}", "SIGNAL")

    # MR engine on active instrument (QQQ if bull, PSQ if bear)
    active = qqq if regime.bull else psq
    m_sig = mr_signal(active, regime, z_len=20, vol_confirm_mult=1.2)
    z_str = f"{m_sig.z:.2f}" if m_sig.z is not None else "NA"
    RF.print_log(f"MR: dir={m_sig.direction}, entry={m_sig.entry}, exit={m_sig.exit}, z={z_str}", "SIGNAL")

    RF.print_log("Signal skeleton OK ✅", "SUCCESS")
