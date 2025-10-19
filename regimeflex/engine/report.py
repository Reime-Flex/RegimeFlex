from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone

def _esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def write_daily_html(result: dict, out_dir: str, filename_prefix: str = "daily_report") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    t = result.get("target", {})
    bc = result.get("breadcrumbs", {}) or {}
    intents = result.get("intents", [])
    pos_after = result.get("positions_after", {})
    snap = result.get("snapshot", {}) or {}

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")
    fname = f"{filename_prefix}_{stamp}.html"
    fpath = Path(out_dir) / fname

    html = []
    html.append("<!doctype html><html><head><meta charset='utf-8'>")
    html.append("<meta name='viewport' content='width=device-width, initial-scale=1' />")
    html.append("<title>RegimeFlex Daily Report</title>")
    # minimal neutral theme
    html.append("<style>body{font-family:Inter,system-ui,Arial,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}"
                "h1{color:#1a237e;margin:0 0 8px} .card{background:#fff;border-radius:12px;padding:16px;margin:12px 0;"
                "box-shadow:0 1px 3px rgba(0,0,0,.05)} .muted{color:#475569} code{background:#e2e8f0;padding:2px 6px;"
                "border-radius:6px} .k{color:#00d4ff}</style></head><body>")
    html.append("<h1>RegimeFlex Daily Report</h1>")
    html.append(f"<div class='muted'>Generated {stamp}</div>")

    # Target
    html.append("<div class='card'>")
    html.append("<h2>Target</h2>")
    html.append("<ul>")
    html.append(f"<li>Direction: <b>{_esc(t.get('direction','FLAT'))}</b></li>")
    html.append(f"<li>Symbol: <code>{_esc(t.get('symbol','NA'))}</code></li>")
    html.append(f"<li>Notional: <b>${t.get('dollars',0.0):,.2f}</b></li>")
    html.append(f"<li>Shares: <b>{t.get('shares',0.0):,.4f}</b></li>")
    html.append(f"<li class='muted'>Notes: <code>{_esc(t.get('notes',''))}</code></li>")
    html.append("</ul>")
    html.append("</div>")

    # Breadcrumbs
    html.append("<div class='card'>")
    html.append("<h2>Breadcrumbs</h2>")
    html.append("<ul>")
    html.append(f"<li>VIX assumption: <b>{bc.get('vix','?')}</b></li>")
    html.append(f"<li>FOMC blackout: <b>{bc.get('fomc_blackout', False)}</b></li>")
    html.append(f"<li>OPEX: <b>{bc.get('opex', False)}</b></li>")
    html.append(f"<li>Phase: <b>{_esc(str(bc.get('phase','')))}</b></li>")
    html.append(f"<li>Config hash: <code>{_esc(str(bc.get('config_hash16','')))}</code></li>")
    html.append("</ul>")
    html.append("</div>")

    # Intents
    html.append("<div class='card'><h2>Planned Orders</h2>")
    if not intents:
        html.append("<div class='muted'>No orders planned.</div>")
    else:
        html.append("<table><thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Type</th><th>TIF</th><th>Limit</th></tr></thead><tbody>")
        for it in intents:
            html.append("<tr>"
                        f"<td><code>{_esc(str(it.get('symbol')))}</code></td>"
                        f"<td>{_esc(str(it.get('side')))}</td>"
                        f"<td>{float(it.get('qty',0.0)):.4f}</td>"
                        f"<td>{_esc(str(it.get('order_type')))}</td>"
                        f"<td>{_esc(str(it.get('time_in_force')))}</td>"
                        f"<td>{'' if it.get('limit_price') is None else f'${float(it.get('limit_price')):.2f}'}</td>"
                        "</tr>")
        html.append("</tbody></table>")
    html.append("</div>")

    # Positions after
    html.append("<div class='card'><h2>Positions After</h2>")
    if not pos_after:
        html.append("<div class='muted'>No holdings.</div>")
    else:
        html.append("<ul>")
        for sym, sh in pos_after.items():
            html.append(f"<li><code>{_esc(str(sym))}</code> — {float(sh):.4f} shares</li>")
        html.append("</ul>")
    html.append("</div>")

    # Snapshot
    html.append("<div class='card'><h2>Daily Snapshot</h2>")
    if not snap:
        html.append("<div class='muted'>No snapshot available.</div>")
    else:
        html.append("<ul>")
        html.append(f"<li>Date (UTC): <b>{_esc(str(snap.get('date','')))}</b></li>")
        html.append(f"<li>Equity (ref): <b>${float(snap.get('equity_ref',0.0)):.2f}</b></li>")
        html.append(f"<li>Total MV (net): <b>${float(snap.get('total_mv',0.0)):.2f}</b></li>")
        html.append(f"<li>Gross Exposure: <b>{float(snap.get('gross_exposure_pct',0.0))*100:.2f}%</b></li>")
        html.append("</ul>")
        html.append("<h3>By Symbol</h3>")
        html.append("<ul>")
        html.append(f"<li>QQQ — MV: ${float(snap.get('QQQ_mv',0.0)):.2f} | Wgt: {float(snap.get('QQQ_w',0.0))*100:.2f}%</li>")
        html.append(f"<li>PSQ — MV: ${float(snap.get('PSQ_mv',0.0)):.2f} | Wgt: {float(snap.get('PSQ_w',0.0))*100:.2f}%</li>")
        html.append("</ul>")
    html.append("</div>")

    html.append("<div class='muted'>© RegimeFlex</div></body></html>")
    fpath.write_text("".join(html), encoding="utf-8")
    return str(fpath)
