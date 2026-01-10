#!/usr/bin/env python
from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF


def esc(x: str) -> str:
    return (
        str(x)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def load_replays_for_month(replays_dir: Path, month: str) -> List[Dict[str, Any]]:
    """
    month: 'YYYY-MM'
    Filters by `as_of` field starting with that month.
    """
    out = []
    for p in sorted(replays_dir.glob("replay_*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        as_of = str(obj.get("as_of",""))
        if not as_of.startswith(month):
            continue
        obj["_path"] = str(p)
        out.append(obj)
    return out


def aggregate_month(replays: List[Dict[str, Any]]) -> Dict[str, Any]:
    days = len(replays)
    no_op_days = 0
    no_op_reasons: Dict[str,int] = {}

    slip_values: List[float] = []
    adv_violations = 0
    liq_counts = {"GREEN":0, "AMBER":0, "RED":0}
    conc_badges = {"net": {"GREEN":0,"AMBER":0,"RED":0},
                   "peak": {"GREEN":0,"AMBER":0,"RED":0}}

    for r in replays:
        bc = r.get("guards",{}) or {}
        metrics = r.get("metrics",{}) or {}

        # no-op
        if bc.get("no_op", False):
            no_op_days += 1
            reason = str(bc.get("no_op_reason","")).strip() or "UNSPECIFIED"
            no_op_reasons[reason] = no_op_reasons.get(reason,0) + 1

        # execution_quality (from metrics.exec_quality.avg_bps)
        eq = metrics.get("exec_quality",{}) or {}
        avg_bps = eq.get("avg_bps")
        if isinstance(avg_bps, (int,float)):
            slip_values.append(float(avg_bps))

        # adv_guardrail (guards.adv_guard)
        adv_guard = bc.get("adv_guard",{}) or {}
        if adv_guard.get("violations"):
            adv_violations += 1

        # liquidity_depth (guards.liquidity_depth)
        liq = bc.get("liquidity_depth",{}) or {}
        cts = liq.get("counts",{}) or {}
        for k in ("GREEN","AMBER","RED"):
            liq_counts[k] += int(cts.get(k,0))

        # exposure_concentration (metrics.exposure_concentration)
        xc = metrics.get("exposure_concentration",{}) or {}
        nb = xc.get("net_badge")
        pb = xc.get("peak_badge")
        if nb in conc_badges["net"]:
            conc_badges["net"][nb] += 1
        if pb in conc_badges["peak"]:
            conc_badges["peak"][pb] += 1

    slip_avg = sum(slip_values)/len(slip_values) if slip_values else None
    slip_sorted = sorted(slip_values)
    if slip_sorted:
        idx = int(round(0.95*(len(slip_sorted)-1)))
        slip_p95 = slip_sorted[idx]
    else:
        slip_p95 = None

    return {
        "days": days,
        "no_op_days": no_op_days,
        "no_op_reasons": no_op_reasons,
        "slip": {
            "count": len(slip_values),
            "avg_bps": slip_avg,
            "p95_bps": slip_p95,
        },
        "adv_violations": adv_violations,
        "liq_counts": liq_counts,
        "conc_badges": conc_badges,
    }


def build_html(month: str, replays: List[Dict[str, Any]], agg: Dict[str, Any]) -> str:
    title = f"RegimeFlex Monthly Analytics — {month}"
    html: List[str] = []

    html.append("<!DOCTYPE html>")
    html.append(f"<html><head><meta charset='utf-8'><title>{esc(title)}</title>")
    html.append("""
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 24px;
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            color: #333;
            line-height: 1.6;
        }
        h1 {
            color: #1a237e;
            border-bottom: 3px solid #1a237e;
            padding-bottom: 12px;
        }
        h2 {
            color: #1a237e;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
            margin-top: 32px;
        }
        h3 {
            color: #666;
            margin-top: 24px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #1a237e;
            color: white;
            font-weight: 600;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        ul {
            margin: 8px 0;
        }
        li {
            margin: 4px 0;
        }
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        }
    </style>
    """)
    html.append("</head><body>")
    html.append(f"<h1>{esc(title)}</h1>")

    # High-level summary
    html.append("<h2>Overview</h2>")
    html.append("<ul>")
    html.append(f"<li>Trading days in month (with replays): <b>{agg['days']}</b></li>")
    html.append(f"<li>No-op days: <b>{agg['no_op_days']}</b></li>")
    html.append(f"<li>ADV guardrail violations (days with any violation): <b>{agg['adv_violations']}</b></li>")
    html.append("</ul>")

    # No-op reasons
    html.append("<h3>No-op reasons</h3>")
    if agg["no_op_reasons"]:
        html.append("<ul>")
        for reason, count in sorted(agg["no_op_reasons"].items(), key=lambda x: x[1], reverse=True):
            html.append(f"<li>{esc(reason)} — <b>{count}</b></li>")
        html.append("</ul>")
    else:
        html.append("<p><i>None</i></p>")

    # Slippage
    s = agg["slip"]
    html.append("<h2>Execution Quality (Slippage)</h2>")
    if s["count"] > 0 and s["avg_bps"] is not None:
        html.append(f"<p>Days with slippage data: <b>{s['count']}</b></p>")
        html.append(f"<p>Average slippage: <b>{s['avg_bps']:.2f} bps</b></p>")
        if s["p95_bps"] is not None:
            html.append(f"<p>95th percentile slippage: <b>{s['p95_bps']:.2f} bps</b></p>")
    else:
        html.append("<p><i>No slippage data recorded this month.</i></p>")

    # Liquidity depth
    lc = agg["liq_counts"]
    html.append("<h2>Liquidity Depth (Order vs ADV)</h2>")
    html.append("<p>Aggregate order checks (sum of GREEN/AMBER/RED across all days):</p>")
    html.append("<ul>")
    html.append(f"<li>GREEN: <b>{lc['GREEN']}</b></li>")
    html.append(f"<li>AMBER: <b>{lc['AMBER']}</b></li>")
    html.append(f"<li>RED: <b>{lc['RED']}</b></li>")
    html.append("</ul>")

    # Exposure concentration
    cb = agg["conc_badges"]
    html.append("<h2>Exposure Concentration</h2>")
    html.append("<h3>Net side concentration</h3>")
    html.append("<ul>")
    for k in ("GREEN","AMBER","RED"):
        html.append(f"<li>{k}: <b>{cb['net'][k]}</b> days</li>")
    html.append("</ul>")

    html.append("<h3>Peak single-symbol concentration</h3>")
    html.append("<ul>")
    for k in ("GREEN","AMBER","RED"):
        html.append(f"<li>{k}: <b>{cb['peak'][k]}</b> days</li>")
    html.append("</ul>")

    # Days table
    html.append("<h2>Days included</h2>")
    html.append("<table>")
    html.append("<thead><tr><th>Date</th><th>No-op?</th><th>No-op reason</th><th>Replay file</th></tr></thead><tbody>")
    for r in replays:
        as_of = r.get("as_of","")
        g = r.get("guards",{}) or {}
        no_op = bool(g.get("no_op", False))
        reason = str(g.get("no_op_reason",""))
        path = r.get("_path","")
        # Extract just the filename from the path
        path_display = Path(path).name if path else ""
        html.append(f"<tr><td>{esc(as_of)}</td>"
                    f"<td>{'Yes' if no_op else 'No'}</td>"
                    f"<td>{esc(reason)}</td>"
                    f"<td><code>{esc(path_display)}</code></td></tr>")
    html.append("</tbody></table>")

    html.append("</body></html>")
    return "\n".join(html)


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(RF.formatted_log("Usage: python scripts/monthly_analytics.py YYYY-MM", "ERROR"))
        return 1

    month = argv[1]
    # Quick validation
    try:
        datetime.strptime(month + "-01", "%Y-%m-%d")
    except ValueError:
        print(RF.formatted_log("ERROR: month must be in format YYYY-MM", "ERROR"))
        return 1

    replays_dir = Path("replays")
    if not replays_dir.exists():
        print(RF.formatted_log(f"Replays directory not found: {replays_dir}", "ERROR"))
        return 1

    replays = load_replays_for_month(replays_dir, month)
    if not replays:
        print(RF.formatted_log(f"No replay files found for month {month}.", "ERROR"))
        return 1

    agg = aggregate_month(replays)
    out_dir = Path("reports/monthly")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"monthly_{month.replace('-','')}.html"
    out_path = out_dir / out_name

    html = build_html(month, replays, agg)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(html, encoding="utf-8")
    import os
    os.replace(tmp, out_path)

    print(RF.formatted_log(f"Monthly analytics written → {out_path}", "SUCCESS"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

