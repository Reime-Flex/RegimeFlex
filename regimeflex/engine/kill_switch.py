# engine/kill_switch.py
from __future__ import annotations
from typing import Dict, Any, List


def evaluate_kill_switch(
    crumbs: Dict[str, Any],
    risk_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Decide whether to trigger the kill switch for *this* run.

    Inputs:
      - crumbs: run breadcrumbs (guards, metrics, etc.)
      - risk_cfg: parsed risk.yaml

    Returns:
      {
        "triggered": bool,
        "reasons": [str, ...],
    }
    """
    ks_cfg = (risk_cfg.get("kill_switch") or {})
    if not ks_cfg.get("enabled", False):
        return {"triggered": False, "reasons": []}

    reasons: List[str] = []

    # Check for existing no-op (can be in guards dict or top-level crumbs)
    guards = crumbs.get("guards", {}) or {}
    existing_no_op = guards.get("no_op", False) or crumbs.get("no_op", False)

    # Respect an existing no-op if configured
    if ks_cfg.get("respect_existing_no_op", True) and existing_no_op:
        # Something else already blocked the run; no need to "double kill".
        return {"triggered": False, "reasons": []}

    # 1) Slippage kill: exec_quality.avg_bps
    # Check both metrics.exec_quality and crumbs.exec_quality (stored at top level)
    metrics = crumbs.get("metrics", {}) or {}
    exec_q = metrics.get("exec_quality", {}) or {}
    if not exec_q:
        exec_q = crumbs.get("exec_quality", {}) or {}
    avg_bps = exec_q.get("avg_bps")
    max_slip = ks_cfg.get("max_slippage_bps")
    if isinstance(avg_bps, (int, float)) and isinstance(max_slip, (int, float)):
        if avg_bps > max_slip:
            reasons.append(
                f"Average slippage {avg_bps:.2f} bps > kill threshold {max_slip:.2f} bps"
            )

    # 2) Liquidity RED checks kill: liquidity_depth.counts.RED
    # Check both guards.liquidity_depth and crumbs.liquidity_depth (stored at top level)
    liq = guards.get("liquidity_depth", {}) or {}
    if not liq:
        liq = crumbs.get("liquidity_depth", {}) or {}
    counts = liq.get("counts", {}) or {}
    red_count = counts.get("RED", 0)
    max_red = ks_cfg.get("max_red_liquidity_checks")
    if isinstance(red_count, (int, float)) and isinstance(max_red, (int, float)):
        if red_count > max_red:
            reasons.append(
                f"Liquidity RED checks {red_count} > kill threshold {max_red}"
            )

    # 3) ADV guard violations kill: adv_guardrail.violations
    # Check both guards.adv_guardrail and crumbs.adv_guardrail (stored at top level)
    # Also check guards.adv_guard (replay pack structure)
    adv_guard = guards.get("adv_guardrail", {}) or {}
    if not adv_guard:
        adv_guard = crumbs.get("adv_guardrail", {}) or {}
    if not adv_guard:
        adv_guard = guards.get("adv_guard", {}) or {}
    violations = adv_guard.get("violations") or []
    if ks_cfg.get("block_on_adv_violation", True):
        if violations:
            reasons.append("ADV guard reported violations in this run")

    return {
        "triggered": bool(reasons),
        "reasons": reasons,
    }

