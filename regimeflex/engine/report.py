from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from regimeflex.engine.health import run_health   # NEW
from regimeflex.engine.incident_view import load_incidents_for_date

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
      .footer{margin-top:18px;font-size:12px;color:#475569}
      .footer code{background:#e2e8f0;padding:1px 4px;border-radius:4px}
    </style>
    """)
    html.append("</head><body>")
    html.append("<h1>RegimeFlex Daily Report</h1>")
    html.append(f"<div class='muted'>Generated {stamp}</div>")

    # Model version
    model = bc.get("model", {}) or {}
    if model:
        html.append(
            f"<p><b>Model:</b> {_esc(model.get('name', 'RegimeFlex'))} "
            f"<code>{_esc(model.get('version', ''))}</code></p>"
        )
    
    # Execution mode
    exec_mode = bc.get("execution_mode", {}) or {}
    dry_run = exec_mode.get("dry_run", False)
    source = exec_mode.get("source", "none")
    mode_str = "DRY-RUN" if dry_run else "LIVE"
    source_map = {
        "env": "environment variable (REGIMEFLEX_DRY_RUN)",
        "config": "config/broker.yaml",
        "none": "default (live)",
    }
    source_str = source_map.get(source, source)
    html.append(f"<p><b>Execution mode:</b> {mode_str} (source: {_esc(source_str)})</p>")

    # Incidents summary
    # Try to get as-of date from breadcrumbs or use today
    as_of = bc.get("price_common_date", "") or bc.get("as_of", "")
    day = as_of or str(datetime.utcnow().date())
    incidents = load_incidents_for_date(".", day=day)
    
    if incidents:
        crit = sum(1 for x in incidents if x.get("level") == "CRITICAL")
        err = sum(1 for x in incidents if x.get("level") == "ERROR")
        warn = sum(1 for x in incidents if x.get("level") == "WARNING")
        html.append(
            f"<p><b>Incidents:</b> {len(incidents)} "
            f"(WARN: {warn}, ERROR: {err}, CRITICAL: {crit})</p>"
        )
    else:
        html.append("<p><b>Incidents:</b> none recorded.</p>")

    # NEW: banner
    cls = "pass" if hstatus=="PASS" else ("warn" if hstatus=="WARN" else "fail")
    icon = "✅" if hstatus=="PASS" else ("⚠️" if hstatus=="WARN" else "❌")
    html.append(f"<div class='banner {cls}'>{icon} Health: {hstatus}</div>")
    
    # Env guard banner
    env_missing = (result.get("breadcrumbs",{}) or {}).get("env_missing", {}) or {}
    env_forced = bool((result.get("breadcrumbs",{}) or {}).get("env_forced_dry_run", False))
    
    if env_forced:
        html.append("<div class='banner warn'>⚠️ ENV GUARD: Missing broker credentials — switched to DRY RUN</div>")
    
    # Panic guard banner
    if (result.get("breadcrumbs",{}) or {}).get("panic_guard_triggered", False):
        html.append("<div class='banner warn'>⚠️ PANIC GUARD — see panic bundle in logs/audit</div>")
    
    # Kill-switch banner
    ks = (result.get("breadcrumbs",{}) or {}).get("kill_switch", {}) or {}
    if ks.get("triggered"):
        html.append("<div class='banner fail'>🛑 KILL-SWITCH TRIGGERED</div>")
        html.append("<ul>")
        for r in ks.get("reasons", []):
            html.append(f"<li>{_esc(r)}</li>")
        html.append("</ul>")
    
    # Bar hygiene banner
    bh_fail = bool((result.get("breadcrumbs",{}) or {}).get("bar_hygiene_fail", False))
    if bh_fail:
        notes = (result.get("breadcrumbs",{}) or {}).get("bar_hygiene_notes", {}) or {}
        act = (result.get("breadcrumbs",{}) or {}).get("bar_hygiene_action", "")
        html.append(f"<div class='banner warn'>⚠️ Bar hygiene failed — {_esc(act)}</div>")
        html.append("<ul>")
        for s, n in notes.items():
            html.append(f"<li><b>{_esc(s)}</b>: {_esc(n)}</li>")
        html.append("</ul>")
    
    if env_missing:
        html.append("<h3>Missing environment variables</h3>")
        html.append("<ul>")
        for subsystem, vars_list in env_missing.items():
            html.append(f"<li><b>{_esc(subsystem)}</b>: <code>{_esc(', '.join(vars_list))}</code></li>")
        html.append("</ul>")

    # Target
    html.append("<div class='card'>")
    html.append("<h2>Target</h2>")
    
    # Cash mode banner
    cash_mode = bool((result.get("breadcrumbs",{}) or {}).get("cash_mode", False))
    if cash_mode:
        html.append("<div class='banner warn'>💤 CASH — no exposure today</div>")
    
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
    
    # Session status
    sess = (result.get("breadcrumbs",{}) or {}).get("session","")
    sess_note = (result.get("breadcrumbs",{}) or {}).get("session_note","")
    if sess:
        html.append(f"<li>Session: <b>{_esc(sess)}</b> <span class='muted'>{_esc(sess_note)}</span></li>")
        # Optional banner when blocked
        if (sess in ("NO_SESSION","HALF_DAY")) and bool((result.get('breadcrumbs',{}) or {}).get('no_op',False)):
            html.append("<div class='banner warn'>⚠️ Session blocked — no orders today</div>")
    
    html.append(f"<li>Phase: <b>{_esc(str(bc.get('phase','')))}</b></li>")
    html.append(f"<li>Positions source: <b>{_esc(str(bc.get('positions_source','')))}</b></li>")
    html.append(f"<li>Equity (live): <b>${float((bc or {}).get('equity_now',0.0)):.2f}</b></li>")
    html.append(f"<li>Price common date: <b>{_esc(str(bc.get('price_common_date','')))}</b></li>")
    
    # Price source table
    ps = bc.get("price_source", {})
    if ps:
        # Get symbols dynamically (could be QQQ/PSQ or TQQQ/SQQQ)
        symbols_found = []
        for key in ps.keys():
            if key not in ("tz_hint",) and isinstance(ps[key], dict):
                symbols_found.append(ps[key])
        if symbols_found:
            html.append("</ul>")
            html.append("<h3>Price Source</h3>")
            html.append("<table><thead><tr><th>Symbol</th><th>Provider</th><th>As-of</th><th>Rows</th></tr></thead><tbody>")
            for row in symbols_found:
                html.append(f"<tr><td>{_esc(row.get('symbol',''))}</td>"
                            f"<td>{_esc(row.get('provider',''))}</td>"
                            f"<td>{_esc(row.get('as_of',''))}</td>"
                            f"<td>{_esc(str(row.get('rows','')))}</td></tr>")
            html.append("</tbody></table>")
            html.append("<ul>")
    
    # Show price staleness information
    stale = (result.get("breadcrumbs",{}) or {}).get("price_stale", False)
    lag  = (result.get("breadcrumbs",{}) or {}).get("price_staleness_days", 0)
    note = (result.get("breadcrumbs",{}) or {}).get("price_stale_note", "")
    
    html.append(f"<li>Price staleness: <b>{int(lag)}d</b> <span class='muted'>{_esc(str(note))}</span></li>")
    
    html.append(f"<li>Plan reason: <code>{_esc(str(result.get('breadcrumbs',{}).get('plan_reason','')))}</code></li>")
    html.append(f"<li>Turnover: <b>{float(bc.get('turnover_frac',0.0))*100:.2f}%</b> <span class='muted'>{_esc(str(bc.get('turnover_note','')))}</span></li>")
    
    # Sanity violation
    sv = (result.get("breadcrumbs",{}) or {}).get("sanity_violation", False)
    if sv:
        html.append(f"<li>Sanity: <b>VIOLATION</b> <span class='muted'>{_esc(str((result.get('breadcrumbs',{}) or {}).get('sanity_note','')))}</span></li>")
    
    # Drift detector
    dr_note = str((result.get("breadcrumbs",{}) or {}).get("drift_note",""))
    dr_warn = bool((result.get("breadcrumbs",{}) or {}).get("drift_warn", False))
    html.append(f"<li>Drift: <b>{'WARN' if dr_warn else dr_note}</b></li>")
    if dr_warn:
        html.append("<div class='banner warn'>⚠️ Position drift exceeds thresholds (see details in logs)</div>")
    dm = (result.get("breadcrumbs",{}) or {}).get("drift_detail", {}) or {}
    if dm:
        html.append("<table><thead><tr><th>Symbol</th><th>Local sh</th><th>Broker sh</th><th>Δ sh</th><th>Δ $</th></tr></thead><tbody>")
        for s, row in dm.items():
            html.append(f"<tr><td>{_esc(s)}</td><td>{row.get('local_sh')}</td><td>{row.get('broker_sh')}</td>"
                        f"<td>{row.get('d_sh')}</td><td>{row.get('d_notional')}</td></tr>")
        html.append("</tbody></table>")
    
    ch = bc.get("config_hash16", "")
    cf = bc.get("config_hash", "")
    if ch:
        html.append(f"<li>Config hash: <code>{_esc(ch)}</code></li>")
    # Optional: collapsible manifest for auditing
    manifest = bc.get("config_manifest", [])
    if manifest:
        html.append("<details><summary>Config manifest</summary><table><thead><tr><th>File</th><th>SHA-256</th></tr></thead><tbody>")
        for rel, d in manifest:
            html.append(f"<tr><td>{_esc(rel)}</td><td><code>{_esc(d)}</code></td></tr>")
        html.append("</tbody></table></details>")
    
    # Rounded shares
    rs = (result.get("breadcrumbs",{}) or {}).get("rounded_shares", {})
    if rs:
        html.append("</ul>")
        html.append("<h3>Rounded Shares</h3>")
        html.append("<table><thead><tr><th>Symbol</th><th>Target Shares</th></tr></thead><tbody>")
        for s, q in rs.items():
            html.append(f"<tr><td>{_esc(s)}</td><td>{q}</td></tr>")
        html.append("</tbody></table>")
        html.append("<ul>")
    
    # Signal stability
    stab = (result.get("breadcrumbs",{}) or {}).get("signal_stability", {}) or {}
    if stab:
        html.append("</ul>")
        html.append("<h3>Signal Stability (last 14 sessions)</h3>")
        if "note" in stab:
            html.append(f"<p class='muted'>{_esc(str(stab.get('note','(no data)')))}</p>")
        else:
            html.append("<table><thead><tr><th>Engine</th><th>Flips</th><th>Score</th><th>N</th></tr></thead><tbody>")
            for eng, row in stab.items():
                flips = row.get("flips", "-")
                score = row.get("score", "-")
                n = row.get("n", "-")
                html.append(f"<tr><td>{_esc(eng)}</td><td>{flips}</td><td>{score}</td><td>{n}</td></tr>")
            html.append("</tbody></table>")
        html.append("<ul>")
    
    # Regime accuracy
    ra = (result.get("breadcrumbs",{}) or {}).get("regime_accuracy", {}) or {}
    if ra:
        html.append("</ul>")
        html.append("<h3>Regime Accuracy</h3>")
        if ra.get("acc") is not None:
            cm = (ra.get("cm", {}) or {})
            html.append(
                f"<p>Lookahead {ra.get('lookahead_days',5)}d · VolWin {ra.get('vol_window',20)} · "
                f"HvThr {float(ra.get('high_vol_thr',0.35)):.2f}</p>"
            )
            html.append(
                f"<p><b>Accuracy</b>: {ra['acc']:.3f} &nbsp; "
                f"TP:{cm.get('TP',0)} TN:{cm.get('TN',0)} FP:{cm.get('FP',0)} FN:{cm.get('FN',0)} N:{cm.get('N',0)}</p>"
            )
        else:
            html.append("<p class='muted'>No score (insufficient history or missing label).</p>")
        html.append("<ul>")
    
    # Config echo
    ce = (result.get("breadcrumbs",{}) or {}).get("config_echo", {})
    if ce:
        html.append(f"<li>Config echo: <code>pair={ce.get('pair','')} eod={ce.get('eod','')} "
                    f"tov={ce.get('turnover','')} cadence={ce.get('cadence','')} minΔ={ce.get('minΔ','')} "
                    f"coal={ce.get('coalesce','')} stale≤{ce.get('stale≤','')} tsi={ce.get('tsi','')} "
                    f"tele={ce.get('tele','')}</code></li>")
    
    html.append(f"<li>Cadence: <b>{'on' if (result.get('breadcrumbs',{}) or {}).get('cadence_enabled') else 'off'}</b> (min {int((result.get('breadcrumbs',{}) or {}).get('cadence_min_days',0))}d)</li>")
    html.append(f"<li>Min Δ exposure: <b>{result.get('breadcrumbs',{}).get('exposure_min_delta','')}</b></li>")
    
    # TSI (Turnover Stability Index)
    avg = float((result.get("breadcrumbs",{}) or {}).get("tsi_avg_turnover", 0.0))
    win = int((result.get("breadcrumbs",{}) or {}).get("tsi_window_days", 7))
    cnt = int((result.get("breadcrumbs",{}) or {}).get("tsi_days_count", 0))
    thr = float((result.get("breadcrumbs",{}) or {}).get("tsi_warn_threshold", 0.25))
    warn = bool((result.get("breadcrumbs",{}) or {}).get("tsi_warn", False))
    
    html.append(f"<li>TSI (avg {win}d): <b>{avg*100:.2f}%</b> over {cnt} day(s) "
                f"{'(warn > ' + f'{thr*100:.0f}%' + ')' if warn else ''}</li>")
    html.append(f"<li>Coalesced flip: <b>{str((result.get('breadcrumbs',{}) or {}).get('coalesced_flip', False))}</b> "
                f"<span class='muted'>{_esc(str((result.get('breadcrumbs',{}) or {}).get('coalesce_note','')))}</span></li>")
    html.append("</ul>")
    
    # Optional: small amber badge if stale
    if stale:
        html.append("<div class='banner warn'>⚠️ Data staleness: prices are older than configured threshold</div>")
    
    # Optional amber banner if TSI warning
    if warn:
        html.append("<div class='banner warn'>⚠️ Elevated turnover: 7-day average above threshold</div>")
    
    # Execution quality
    eq = (result.get("breadcrumbs",{}) or {}).get("exec_quality", {}) or {}
    if eq:
        html.append("<h3>Execution Quality</h3>")
        if eq.get("count",0) > 0 and eq.get("avg_bps") is not None:
            html.append(f"<p>Ref: <code>{_esc(eq.get('ref',''))}</code> · Window {eq.get('window',20)} trades</p>")
            html.append(f"<p><b>Avg slippage</b>: {eq['avg_bps']} bps &nbsp; <b>p95</b>: {eq['p95_bps']} bps &nbsp; "
                        f"<span class='muted'>(n={eq['count']})</span></p>")
        else:
            html.append("<p class='muted'>No fills yet or dry_run — slippage n/a.</p>")
    
    # Exposure concentration
    xc = (result.get("breadcrumbs",{}) or {}).get("exposure_concentration", {}) or {}
    if xc:
        def pill(txt):
            m = {"GREEN":"#10b981","AMBER":"#f59e0b","RED":"#ef4444"}
            return f"<span style='padding:2px 8px;border-radius:999px;background:{m.get(txt,'#94a3b8')};color:white;font-weight:600'>{txt}</span>"
        html.append("<h3>Exposure Concentration</h3>")
        html.append(f"<p>Net side: <b>{xc.get('net_abs',0):.2%}</b> {pill(xc.get('net_badge',''))}</p>")
        if xc.get("peak_symbol"):
            html.append(f"<p>Top symbol ({_esc(xc['peak_symbol'])})}: <b>{xc.get('peak_abs',0):.2%}</b> {pill(xc.get('peak_badge',''))}</p>")
    
    # Liquidity depth
    liq = (result.get("breadcrumbs",{}) or {}).get("liquidity_depth", {}) or {}
    if liq and liq.get("rows"):
        def pill(txt):
            colors = {"GREEN":"#10b981","AMBER":"#f59e0b","RED":"#ef4444"}
            return f"<span style='padding:2px 8px;border-radius:999px;background:{colors.get(txt,'#94a3b8')};color:white;font-weight:600'>{txt}</span>"
        html.append("<h3>Liquidity Depth (Order vs ADV)</h3>")
        cts = liq.get("counts", {})
        html.append(f"<p>Summary: GREEN {cts.get('GREEN',0)} · AMBER {cts.get('AMBER',0)} · RED {cts.get('RED',0)}</p>")
        html.append("<table><thead><tr><th>Symbol</th><th>Qty</th><th>Price</th><th>Notional</th><th>ADV</th><th>%ADV</th><th>Badge</th></tr></thead><tbody>")
        for r in liq.get("rows", []):
            html.append(f"<tr><td>{_esc(r['symbol'])}</td>"
                        f"<td>{r['qty']}</td>"
                        f"<td>{r['price']:.2f}</td>"
                        f"<td>{r['notional']:.2f}</td>"
                        f"<td>{r['adv']:.2f}</td>"
                        f"<td>{r['of_adv']*100:.2f}%</td>"
                        f"<td>{pill(r['badge'])}</td></tr>")
        html.append("</tbody></table>")
    
    # Fill-quality drift
    fd = (result.get("breadcrumbs",{}) or {}).get("fill_quality_drift", {}) or {}
    if fd:
        html.append("<h3>Fill-Quality Drift</h3>")
        curr = fd.get("current_avg")
        base = fd.get("baseline_avg")
        d = fd.get("delta_bps")
        thr = fd.get("threshold_bps", 0.0)
        if curr is None or base is None:
            html.append("<p class='muted'>Not enough data for drift (need baseline & recent fills).</p>")
        else:
            badge = "<span style='background:#ef4444;color:#fff;padding:2px 8px;border-radius:999px;font-weight:600'>ALERT</span>" if fd.get("alert") else "<span style='background:#10b981;color:#fff;padding:2px 8px;border-radius:999px;font-weight:600'>OK</span>"
            baseline_days = fd.get("baseline_days", 30)
            html.append(f"<p>Current(⟂{fd.get('count_current',0)}): <b>{curr} bps</b> · Baseline(⟂{fd.get('count_baseline',0)} in {baseline_days}d): <b>{base} bps</b></p>")
            html.append(f"<p>Δ = <b>{d} bps</b> · Threshold {thr} bps → {badge}</p>")
    
    # ADV guardrail
    ag = (result.get("breadcrumbs",{}) or {}).get("adv_guardrail", {}) or {}
    if ag and ag.get("violations"):
        html.append("<h3>ADV Guardrail</h3>")
        html.append(f"<p>Action: <code>{_esc(ag.get('action',''))}</code> · Cap: {ag.get('crit_frac',0):.2%}</p>")
        html.append("<table><thead><tr><th>Symbol</th><th>Qty</th><th>Notional</th><th>ADV</th><th>%ADV</th><th>MaxQty@Cap</th></tr></thead><tbody>")
        for v in ag["violations"]:
            html.append(f"<tr><td>{_esc(v['symbol'])}</td>"
                        f"<td>{v['qty']:.0f}</td>"
                        f"<td>{v['notional']:.2f}</td>"
                        f"<td>{v['adv']:.2f}</td>"
                        f"<td>{v['of_adv']*100:.2f}%</td>"
                        f"<td>{v['max_qty']:.0f}</td></tr>")
        html.append("</tbody></table>")
        if (result.get("breadcrumbs",{}) or {}).get("no_op_reason","") == "ADV_GUARD":
            html.append("<div class='banner warn'>⚠️ Run blocked by ADV guardrail</div>")
    
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

    # Footer: duration + versions
    bc = result.get("breadcrumbs",{}) or {}
    dur = float(bc.get("run_duration_sec", 0.0))
    vers = bc.get("versions", {}) or {}
    html.append("<div class='footer'>")
    html.append(f"⏱️ Run duration: <b>{dur:.3f}s</b><br/>")
    if vers:
        html.append("🔧 Runtime: ")
        html.append(f"<code>python {vers.get('python','')}</code> · ")
        html.append(f"<code>pandas {vers.get('pandas','')}</code> · ")
        html.append(f"<code>numpy {vers.get('numpy','')}</code> · ")
        html.append(f"<code>alpaca_trade_api {vers.get('alpaca_trade_api','')}</code> · ")
        html.append(f"<code>python-telegram-bot {vers.get('python_telegram_bot','')}</code>")
    rh = bc.get("report_sha256", "")
    if rh:
        html.append(f"<div class='small' style='margin-top:8px;font-size:11px;color:#64748b'>Report SHA-256: <code>{_esc(rh)}</code></div>")
    html.append("</div>")

    html.append("<div class='muted'>© RegimeFlex</div></body></html>")
    fpath.write_text("".join(html), encoding="utf-8")
    return str(fpath)
