#!/usr/bin/env python
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.incident_view import load_incidents_for_date


def esc(x: str) -> str:
    return (
        str(x)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def load_latest_replay(replays_dir: Path) -> Dict[str, Any]:
    """Load the most recent replay pack by modification time."""
    files = sorted(replays_dir.glob("replay_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No replay_*.json found in replays/")
    path = files[0]
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["_path"] = str(path)
    return obj


def build_html(pack: Dict[str, Any]) -> str:
    ann = pack.get("annotation", {}) or {}
    bc = pack.get("guards", {}) or {}
    metrics = pack.get("metrics", {}) or {}
    prov = pack.get("provenance", {}) or {}
    state = pack.get("state", {}) or {}

    model = prov.get("model", {}) or pack.get("model", {}) or {}
    exec_mode = prov.get("execution_mode", {}) or {}
    dry_run = bool(exec_mode.get("dry_run", False))
    source = exec_mode.get("source", "none")
    incidents = pack.get("_incidents", []) or []
    
    # Get anomalies from breadcrumbs (stored in replay pack)
    bc_full = pack.get("breadcrumbs", {}) or {}
    anomalies = bc_full.get("anomalies", {}) or {}
    ps_check = bc_full.get("price_source_check", {}) or {}

    as_of = pack.get("as_of", "")
    ts_utc = pack.get("ts_utc", "")
    replay_path = pack.get("_path", "")
    # Extract just the filename for display
    replay_display = Path(replay_path).name if replay_path else ""

    no_op = bool(bc.get("no_op", False))
    no_op_reason = str(bc.get("no_op_reason", ""))

    exec_q = metrics.get("exec_quality", {}) or {}
    slip_avg = exec_q.get("avg_bps")
    slip_last = exec_q.get("last_trade_bps")

    adv_guard = bc.get("adv_guard", {}) or {}
    adv_viol = adv_guard.get("violations") or []

    liq = bc.get("liquidity_depth", {}) or {}
    liq_counts = liq.get("counts", {}) or {}

    positions_after = state.get("positions_after", {}) or {}

    title = f"RegimeFlex Status — {as_of}"

    html: List[str] = []
    html.append("<!DOCTYPE html>")
    html.append(f"<html><head><meta charset='utf-8'><title>{esc(title)}</title>")
    html.append("""
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 24px;
            background: #f8fafc;
            color: #111827;
            max-width: 1200px;
            margin: 0 auto;
            line-height: 1.6;
        }
        h1 {
            margin-bottom: 4px;
            color: #1a237e;
        }
        h2 {
            margin-top: 0;
            margin-bottom: 8px;
            color: #1a237e;
            font-size: 1.25em;
        }
        h3 {
            margin-bottom: 4px;
            color: #666;
            font-size: 1em;
        }
        section {
            margin-bottom: 24px;
            padding: 16px;
            border-radius: 12px;
            background: #fff;
            border: 1px solid #e5e7eb;
        }
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        }
        pre {
            background: #f9fafb;
            padding: 8px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            overflow-x: auto;
            font-size: 13px;
        }
        ul {
            margin: 8px 0;
        }
        li {
            margin: 4px 0;
        }
    </style>
    """)
    html.append("</head><body>")

    # Header
    html.append(f"<h1>{esc(title)}</h1>")
    html.append(f"<p style='margin-top:0;color:#6b7280;'>Replay: <code>{esc(replay_display)}</code> · ts_utc: {esc(ts_utc)}</p>")

    # Model + config
    html.append("<section>")
    html.append("<h2>Model</h2>")
    html.append(f"<p><b>Name:</b> {esc(model.get('name','RegimeFlex'))} <code>{esc(model.get('version',''))}</code></p>")
    desc = model.get('description','')
    if desc:
        html.append(f"<p><b>Description:</b> {esc(desc)}</p>")
    html.append("</section>")

    # Run state
    status_color = "#10b981" if not no_op else "#f59e0b"
    status_label = "ACTIVE (trading allowed)" if not no_op else "NO-OP (blocked)"
    mode_label = "DRY-RUN" if dry_run else "LIVE"
    mode_color = "#f59e0b" if dry_run else "#10b981"
    mode_source_map = {
        "env": "environment variable (REGIMEFLEX_DRY_RUN)",
        "config": "config/broker.yaml",
        "none": "default (live)",
    }
    mode_source = mode_source_map.get(source, source)
    html.append(f"""
    <section>
      <h2>Run Status</h2>
      <p>
        <span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{status_color};color:#fff;font-weight:600;'>{esc(status_label)}</span>
        &nbsp;
        <span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{mode_color};color:#fff;font-weight:600;'>Mode: {esc(mode_label)}</span>
      </p>
      <p><b>Execution mode source:</b> {esc(mode_source)}</p>
      <p><b>No-op:</b> {no_op}</p>
      {f"<p><b>No-op reason:</b> {esc(no_op_reason)}</p>" if no_op_reason else ""}
    </section>
    """)

    # Positions
    html.append("<section>")
    html.append("<h2>Positions (after last run)</h2>")
    if positions_after:
        html.append("<ul>")
        for sym, qty in sorted(positions_after.items()):
            html.append(f"<li><code>{esc(sym)}</code>: {qty}</li>")
        html.append("</ul>")
    else:
        html.append("<p><i>No positions recorded.</i></p>")
    html.append("</section>")

    # Execution / slippage
    html.append("<section>")
    html.append("<h2>Execution Quality</h2>")
    if slip_avg is not None:
        html.append(f"<p><b>Average slippage:</b> {slip_avg:.2f} bps</p>")
    else:
        html.append("<p><b>Average slippage:</b> n/a</p>")
    if slip_last is not None:
        html.append(f"<p><b>Last trade slippage:</b> {slip_last:.2f} bps</p>")
    html.append("</section>")

    # Liquidity depth + ADV guard
    html.append("<section>")
    html.append("<h2>Liquidity & ADV Guard</h2>")
    html.append("<h3>Liquidity depth summary</h3>")
    html.append("<ul>")
    html.append(f"<li>GREEN checks: {liq_counts.get('GREEN',0)}</li>")
    html.append(f"<li>AMBER checks: {liq_counts.get('AMBER',0)}</li>")
    html.append(f"<li>RED checks: {liq_counts.get('RED',0)}</li>")
    html.append("</ul>")

    html.append("<h3>ADV guardrail</h3>")
    if adv_viol:
        html.append(f"<p><b>Violations:</b> {len(adv_viol)}</p>")
        html.append("<pre>")
        html.append(esc(json.dumps(adv_viol, indent=2, ensure_ascii=False)))
        html.append("</pre>")
    else:
        html.append("<p><i>No ADV violations in last run.</i></p>")
    html.append("</section>")

    # Annotation (optional)
    html.append("<section>")
    html.append("<h2>Annotation</h2>")
    html.append(f"<p><b>Summary:</b> {esc(ann.get('summary',''))}</p>")
    html.append(f"<p><b>Intents count:</b> {ann.get('intents',0)}</p>")
    html.append("</section>")

    # Incidents
    html.append("<section style='margin-bottom:24px;padding:16px;border-radius:12px;background:#fff;border:1px solid #e5e7eb;'>")
    html.append("<h2 style='margin-top:0;margin-bottom:8px;'>Incidents</h2>")

    if incidents:
        # Show a small badge summary
        crit = sum(1 for x in incidents if x.get("level") == "CRITICAL")
        err = sum(1 for x in incidents if x.get("level") == "ERROR")
        warn = sum(1 for x in incidents if x.get("level") == "WARNING")

        html.append("<p>")
        html.append(f"<b>Total:</b> {len(incidents)} &nbsp; ")
        html.append(f"<span>⚠️ WARN: {warn}</span> &nbsp; ")
        html.append(f"<span>❌ ERROR: {err}</span> &nbsp; ")
        html.append(f"<span>🔥 CRITICAL: {crit}</span>")
        html.append("</p>")

        html.append("<ul>")
        # Show latest few
        for x in incidents[-5:]:
            ts = x.get("timestamp","")
            lvl = x.get("level","")
            msg = x.get("message","")
            html.append(f"<li><code>{esc(lvl)}</code> [{esc(ts)}]: {esc(msg)}</li>")
        html.append("</ul>")
    else:
        html.append("<p><i>No incidents recorded for this day.</i></p>")

    html.append("</section>")

    # Anomalies
    html.append("<section style='margin-bottom:24px;padding:16px;border-radius:12px;background:#fff;border:1px solid #e5e7eb;'>")
    html.append("<h2 style='margin-top:0;margin-bottom:8px;'>Anomalies</h2>")
    if anomalies.get("any"):
        sl = anomalies.get("slippage", {}) or {}
        lq = anomalies.get("liquidity", {}) or {}
        html.append("<ul>")
        if sl.get("flagged"):
            html.append(f"<li><b>Slippage:</b> {esc(sl.get('reason',''))}</li>")
        if lq.get("flagged"):
            html.append(f"<li><b>Liquidity:</b> {esc(lq.get('reason',''))}</li>")
        html.append("</ul>")
    else:
        html.append("<p><i>No anomalies flagged for this run.</i></p>")
    html.append("</section>")

    # Price Source check
    ok_ps = ps_check.get("ok", False)
    reason_ps = ps_check.get("reason", "")
    html.append("<section style='margin-bottom:24px;padding:16px;border-radius:12px;background:#fff;border:1px solid #e5e7eb;'>")
    html.append("<h2 style='margin-top:0;margin-bottom:8px;'>Price Source</h2>")
    if ok_ps:
        html.append("<p><b>Metadata:</b> OK (non-empty dict)</p>")
    else:
        html.append("<p><b>Metadata:</b> <span style='color:#b91c1c;'>Issue detected</span></p>")
        if reason_ps:
            html.append(f"<p><b>Reason:</b> {esc(reason_ps)}</p>")
    html.append("</section>")

    html.append("</body></html>")
    return "\n".join(html)


def main(argv) -> int:
    root = Path(".")
    replays_dir = root / "replays"
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "status.html"

    try:
        pack = load_latest_replay(replays_dir)
    except FileNotFoundError as e:
        print(RF.formatted_log(str(e), "ERROR"))
        return 1

    # Load incidents for the as-of date
    as_of = pack.get("as_of", "")
    day = as_of or str(datetime.now(timezone.utc).date())
    incidents = load_incidents_for_date(".", day=day)
    pack["_incidents"] = incidents

    html = build_html(pack)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(html, encoding="utf-8")
    import os
    os.replace(tmp, out_path)

    print(RF.formatted_log(f"Status dashboard written → {out_path}", "SUCCESS"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

