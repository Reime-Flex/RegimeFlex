# engine/anomaly.py
from __future__ import annotations
from typing import Dict, Any


def detect_anomalies(
    crumbs: Dict[str, Any],
    risk_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Detect non-fatal anomalies in the current run.
    
    Returns:
      {
        "slippage": {
          "flagged": bool,
          "reason": str | None,
        },
        "liquidity": {
          "flagged": bool,
          "reason": str | None,
        },
        "any": bool,
      }
    """
    alerts_cfg = (risk_cfg.get("anomaly_alerts") or {})
    if not alerts_cfg.get("enabled", False):
        return {
            "slippage": {"flagged": False, "reason": None},
            "liquidity": {"flagged": False, "reason": None},
            "any": False,
        }

    metrics = crumbs.get("metrics", {}) or {}
    guards = crumbs.get("guards", {}) or {}

    out = {
        "slippage": {"flagged": False, "reason": None},
        "liquidity": {"flagged": False, "reason": None},
        "any": False,
    }

    # 1) Slippage anomaly (soft threshold)
    exec_q = metrics.get("exec_quality", {}) or {}
    # Also check crumbs.exec_quality (it might be stored there)
    if not exec_q:
        exec_q = crumbs.get("exec_quality", {}) or {}
    avg_bps = exec_q.get("avg_bps")
    soft_slip = alerts_cfg.get("slippage_soft_bps")
    if isinstance(avg_bps, (int, float)) and isinstance(soft_slip, (int, float)):
        if avg_bps > soft_slip:
            out["slippage"]["flagged"] = True
            out["slippage"]["reason"] = (
                f"Average slippage {avg_bps:.2f} bps > soft threshold {soft_slip:.2f} bps"
            )

    # 2) Liquidity anomaly (RED checks soft threshold)
    # Check both guards.liquidity_depth and crumbs.liquidity_depth (stored at top level)
    liq = guards.get("liquidity_depth", {}) or {}
    if not liq:
        liq = crumbs.get("liquidity_depth", {}) or {}
    counts = liq.get("counts", {}) or {}
    red_count = counts.get("RED", 0)
    soft_red = alerts_cfg.get("liquidity_red_soft")
    if isinstance(red_count, (int, float)) and isinstance(soft_red, (int, float)):
        if red_count > soft_red:
            out["liquidity"]["flagged"] = True
            out["liquidity"]["reason"] = (
                f"Liquidity RED checks {red_count} > soft threshold {soft_red}"
            )

    out["any"] = out["slippage"]["flagged"] or out["liquidity"]["flagged"]
    return out

