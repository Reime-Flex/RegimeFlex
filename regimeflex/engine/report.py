from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from .health import run_health   # NEW

def _esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def write_daily_html(result: dict, out_dir: str, filename_prefix: str = "daily_report") -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    t = result.get("target", {})
    bc = result.get("breadcrumbs", {}) or {}
    intents = result.get("intents", [])
    pos_after = result.get("positions_after", {})
    snap = result.get("snapshot", {}) or {}

    # NEW: health snapshot for this render
    health = run_health()
    hstatus = health.status  # "PASS" | "WARN" | "FAIL"

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")
    fname = f"{filename_prefix}_{stamp}.html"
    fpath = Path(out_dir) / fname

    html = []
    html.append("<!doctype html><html><head><meta charset='utf-8'>")
    html.append("<meta name='viewport' content='width=device-width, initial-scale=1' />")
    html.append("<title>RegimeFlex Daily Report</title>")
    # styles + banner theme
    html.append("""
    <style>
      :root{
        --pass:#10b981; /* emerald */
        --warn:#f59e0b; /* gold */
        --fail:#ef4444; /* ruby */
        --ink:#0f172a;  --panel:#fff; --bg:#f8fafc; --brand:#1a237e;
      }
      body{font-family:Inter,system-ui,Arial,sans-serif;margin:24px;background:var(--bg);color:var(--ink)}
      h1{color:var(--brand);margin:0 0 8px}
      .card{background:var(--panel);border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
      .muted{color:#475569} code{background:#e2e8f0;padding:2px 6px;border-radius:6px}
      .banner{padding:10px 14px;border-radius:10px;margin:0 0 14px;font-weight:600;display:inline-block}
      .pass{background:rgba(16,185,129,.10);color:var(--pass);border:1px solid rgba(16,185,129,.35)}
      .warn{background:rgba(245,158,11,.10);color:var(--warn);border:1px solid rgba(245,158,11,.35)}
      .fail{background:rgba(239,68,68,.10);color:var(--fail);border:1px solid rgba(239,68,68,.35)}
      table{border-collapse:collapse;width:100%} th,td{padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:left}
    </style>
    """)
    html.append("</head><body>")
    html.append("<h1>RegimeFlex Daily Report</h1>")
    html.append(f"<div class='muted'>Generated {stamp}</div>")

    # NEW: banner
    cls = "pass" if hstatus=="PASS" else ("warn" if hstatus=="WARN" else "fail")
    icon = "✅" if hstatus=="PASS" else ("⚠️" if hstatus=="WARN" else "❌")
    html.append(f"<div class='banner {cls}'>{icon} Health: {hstatus}</div>")

    # Target
    html.append("<div class='card'>")
    html.append("<h2>Target</h2>")
    html.append("<ul>")
    html.append(f"<li>Direction: <b>{_esc(t.get('direction','FLAT'))}</b></li>")
    html.append(f"<li>Symbol: <code>{_esc(t.get('symbol','NA'))}</code></li>")
    html.append(f"<li>Notional: <b>${t.get('dollars',0.0):,.2f}</b></li>")
    html.append(f"<li>Shares: <b>{t.get('shares',0.0):,.4f}</b></li>")
    html.append(f"<li class='muted'>Notes: <code>{_esc(t.get('notes',''))}</code></li>")
    
    # Show no-op reason if present
    no_op = bool((result.get("breadcrumbs",{}) or {}).get("no_op", False))
    if no_op:
        reason = (result.get("breadcrumbs",{}) or {}).get("no_op_reason","")
        html.append(f"<div class='muted'>No-op day: <b>{_esc(str(reason))}</b></div>")
    
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
    html.append(f"<li>Positions source: <b>{_esc(str(bc.get('positions_source','')))}</b></li>")
    html.append(f"<li>Equity (live): <b>${float((bc or {}).get('equity_now',0.0)):.2f}</b></li>")
    html.append(f"<li>Plan reason: <code>{_esc(str(result.get('breadcrumbs',{}).get('plan_reason','')))}</code></li>")
    html.append(f"<li>Turnover: <b>{float(bc.get('turnover_frac',0.0))*100:.2f}%</b> <span class='muted'>{_esc(str(bc.get('turnover_note','')))}</span></li>")
    html.append(f"<li>Config hash: <code>{_esc(str(bc.get('config_hash16','')))}</code></li>")
    html.append("</ul>")
    
    # Exposure delta mini-table
    prev = (result.get("breadcrumbs",{}) or {}).get("prev_exposure", {})
    des  = (result.get("breadcrumbs",{}) or {}).get("desired_exposure", {})
    dlt  = (result.get("breadcrumbs",{}) or {}).get("delta_exposure", {})
    html.append("<h3>Exposure Change</h3>")
    html.append("<table><thead><tr><th>Side</th><th>Prev</th><th>Desired</th><th>Δ</th></tr></thead><tbody>")
    def pct(x): 
        try: return f"{float(x)*100:.2f}%"
        except: return "0.00%"
    
    # Use dynamic execution pair labels
    exec_long = (result.get("breadcrumbs",{}) or {}).get("exec_long","LONG")
    exec_short = (result.get("breadcrumbs",{}) or {}).get("exec_short","SHORT")
    sides = [exec_long, exec_short]
    
    for side in sides:
        html.append("<tr>"
                    f"<td>{_esc(side)}</td>"
                    f"<td>{pct(prev.get(side,0))}</td>"
                    f"<td>{pct(des.get(side,0))}</td>"
                    f"<td>{pct(dlt.get(side,0))}</td>"
                    "</tr>")
    html.append("</tbody></table>")
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
