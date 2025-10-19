# engine/guardrails.py
from __future__ import annotations
from typing import Dict, Tuple
from .config import Config
from .identity import RegimeFlexIdentity as RF

def enforce_exposure_caps(weights: Dict[str, float]) -> Tuple[Dict[str, float], str]:
    """
    Caps per-side and total gross exposure. Returns (new_weights, note).
    Input/Output weights are fractions of equity (e.g., 0.85 == 85%).
      keys expected: "TQQQ", "SQQQ" (missing keys treated as 0).
    """
    cfg = Config(".")._load_yaml("config/exposure.yaml")
    lim = (cfg.get("limits") or {})
    cap_gross = float(lim.get("max_gross", 1.0))
    cap_t = float(lim.get("max_tqqq", 1.0))
    cap_s = float(lim.get("max_sqqq", 1.0))

    t = max(0.0, float(weights.get("TQQQ", 0.0)))
    s = max(0.0, float(weights.get("SQQQ", 0.0)))

    note_parts = []

    # per-side caps
    t0, s0 = t, s
    if t > cap_t:
        t = cap_t
        note_parts.append(f"TQQQ capped→{cap_t:.2f}")
    if s > cap_s:
        s = cap_s
        note_parts.append(f"SQQQ capped→{cap_s:.2f}")

    # gross cap (|t| + |s|)
    gross = t + s
    if gross > cap_gross and gross > 0:
        scale = cap_gross / gross
        t *= scale
        s *= scale
        note_parts.append(f"gross scaled×{scale:.3f}")

    changed = (abs(t - t0) > 1e-9) or (abs(s - s0) > 1e-9)
    note = " | ".join(note_parts) if changed else "OK"
    out = {"TQQQ": float(t), "SQQQ": float(s)}
    if changed:
        RF.print_log(f"Exposure guardrails applied: {note}", "RISK")
    return out, note
