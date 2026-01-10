#!/usr/bin/env python
from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF

def esc(x: str) -> str:
    """Escape HTML special characters."""
    return (
        str(x)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

def block(title: str, body: str) -> str:
    """Create a styled section block."""
    return f"""
    <section style="margin-bottom:24px; border:1px solid #e0e0e0; border-radius:4px; padding:16px; background:#fafafa;">
      <h2 style="border-bottom:2px solid #1a237e; padding-bottom:8px; margin-top:0; color:#1a237e;">{esc(title)}</h2>
      {body}
    </section>
    """

def format_dict(d: dict, indent: int = 0) -> str:
    """Format a dictionary as HTML with better readability."""
    if not d:
        return "<em>Empty</em>"
    
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            items.append(f"<b>{esc(str(k))}:</b><br/><div style='margin-left:20px;'>{format_dict(v, indent+1)}</div>")
        elif isinstance(v, list):
            items.append(f"<b>{esc(str(k))}:</b> {format_list(v)}")
        else:
            items.append(f"<b>{esc(str(k))}:</b> {esc(str(v))}")
    
    return "<br/>".join(items)

def format_list(lst: list) -> str:
    """Format a list as HTML."""
    if not lst:
        return "<em>Empty</em>"
    
    items = []
    for i, item in enumerate(lst):
        if isinstance(item, dict):
            items.append(f"<div style='margin-left:20px; margin-bottom:8px;'><b>Item {i+1}:</b><br/>{format_dict(item)}</div>")
        else:
            items.append(f"<div style='margin-left:20px;'>{esc(str(item))}</div>")
    
    return "<br/>".join(items)

def main(argv):
    if len(argv) != 2:
        print(RF.formatted_log("Usage: python scripts/replay_viewer.py path/to/replay.json", "ERROR"))
        return 1

    path = Path(argv[1])
    if not path.exists():
        print(RF.formatted_log(f"Replay pack not found: {path}", "ERROR"))
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(RF.formatted_log(f"Invalid JSON in replay pack: {e}", "ERROR"))
        return 1
    except Exception as e:
        print(RF.formatted_log(f"Error reading replay pack: {e}", "ERROR"))
        return 1

    out_dir = Path("replays/viewers")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Name the HTML report
    asof = data.get("as_of", "unknown")
    ts = datetime.now(timezone.utc).strftime("%H%MZ")
    out_name = f"replay_view_{asof.replace('-','')}_{ts}.html"
    out_path = out_dir / out_name

    # --------------------------------------------------
    # Build HTML parts
    # --------------------------------------------------

    html = []
    
    # HTML head with styling
    html.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>Replay View {}</title>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 24px;
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            color: #333;
            line-height: 1.6;
        }}
        h1 {{
            color: #1a237e;
            border-bottom: 3px solid #1a237e;
            padding-bottom: 12px;
        }}
        pre {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 12px;
            overflow-x: auto;
            font-size: 13px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        }}
        .meta {{
            background: #e3f2fd;
            border-left: 4px solid #1a237e;
            padding: 12px;
            margin-bottom: 24px;
        }}
    </style>
</head>
<body>""".format(esc(asof)))

    # Header with metadata
    brand = data.get("brand", {})
    ts_utc = data.get("ts_utc", "")
    html.append(f"""
    <h1>Replay Viewer</h1>
    <div class="meta">
        <p><b>As-of Date:</b> {esc(asof)}</p>
        <p><b>Timestamp (UTC):</b> {esc(ts_utc)}</p>
        <p><b>Brand:</b> {esc(brand.get("name", ""))}</p>
        <p><b>Config Hash:</b> <code>{esc(brand.get("config_hash16", ""))}</code></p>
    </div>
    """)

    # Annotation
    ann = data.get("annotation", {})
    html.append(block("Annotation", f"""
        <p><b>Summary:</b> {esc(ann.get("summary", ""))}</p>
        <p><b>Intents:</b> {ann.get("intents", 0)}</p>
        <p><b>No-op:</b> {ann.get("no_op", False)}</p>
        <p><b>No-op reason:</b> {esc(ann.get("no_op_reason", ""))}</p>
        <p><b>Long Symbol:</b> {esc(ann.get("long_sym", ""))}</p>
        <p><b>Short Symbol:</b> {esc(ann.get("short_sym", ""))}</p>
    """))

    # State
    state = data.get("state", {})
    positions_before = state.get("positions_before", {})
    positions_after = state.get("positions_after", {})
    intents = state.get("intents", [])
    
    html.append(block("State", f"""
        <h3 style="color:#666; margin-top:0;">Positions BEFORE</h3>
        <pre>{esc(json.dumps(positions_before, indent=2, ensure_ascii=False))}</pre>
        
        <h3 style="color:#666; margin-top:16px;">Intents</h3>
        {format_list(intents) if intents else "<em>No intents</em>"}
        
        <h3 style="color:#666; margin-top:16px;">Positions AFTER</h3>
        <pre>{esc(json.dumps(positions_after, indent=2, ensure_ascii=False))}</pre>
    """))

    # Guards
    gr = data.get("guards", {})
    html.append(block("Guards", f"""
        <pre>{esc(json.dumps(gr, indent=2, ensure_ascii=False))}</pre>
    """))

    # Metrics
    mt = data.get("metrics", {})
    html.append(block("Metrics", f"""
        <pre>{esc(json.dumps(mt, indent=2, ensure_ascii=False))}</pre>
    """))

    # Symbol bars
    syms = data.get("symbols", {})
    if syms:
        rows = ""
        for sym, obj in syms.items():
            last_price = obj.get("last_price", "N/A")
            bars_tail = obj.get("bars_tail", [])
            rows += f"""
            <div style="margin-bottom:20px; padding:12px; background:#fff; border:1px solid #ddd; border-radius:4px;">
                <h3 style="margin-top:0; color:#1a237e;">{esc(sym)}</h3>
                <p><b>Last price:</b> {last_price}</p>
                <p><b>Price tail ({len(bars_tail)} bars):</b></p>
                <pre>{esc(json.dumps(bars_tail, indent=2, ensure_ascii=False))}</pre>
            </div>
            """
        html.append(block("Symbol Tails", rows))
    else:
        html.append(block("Symbol Tails", "<em>No symbol data available</em>"))

    # Provenance
    prov = data.get("provenance", {})
    model = prov.get("model", {}) or {}
    model_html = ""
    if model and model.get("name"):
        model_html = f"<p><b>Model:</b> {esc(model.get('name', ''))} <code>{esc(model.get('version', ''))}</code></p>"
    html.append(block("Provenance", f"""
        {model_html}
        <pre>{esc(json.dumps(prov, indent=2, ensure_ascii=False))}</pre>
    """))

    html.append("</body></html>")

    # Save atomically
    try:
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text("\n".join(html), encoding="utf-8")
        tmp.replace(out_path)
        print(RF.formatted_log(f"Replay HTML viewer written → {out_path}", "SUCCESS"))
        return 0
    except Exception as e:
        print(RF.formatted_log(f"Error writing HTML viewer: {e}", "ERROR"))
        return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

