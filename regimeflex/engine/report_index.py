# engine/report_index.py
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import html

REPORTS_DIR = Path("reports")

def _collect(patterns: List[str]) -> List[Tuple[str, Path]]:
    items: List[Tuple[str, Path]] = []
    for pat in patterns:
        for p in sorted(REPORTS_DIR.glob(pat), key=lambda x: x.stat().st_mtime, reverse=True):
            items.append((p.name, p))
    # de-dup if patterns overlap
    seen, dedup = set(), []
    for name, p in items:
        if name in seen: 
            continue
        seen.add(name)
        dedup.append((name, p))
    return dedup

def build_index(max_items: int = 30, title: str = "RegimeFlex — Reports") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    html_reports = _collect(["daily_report_*.html"])
    csvs_changes = _collect(["changes_*.csv"])
    csvs_orders  = _collect(["orders_preview_*.csv"])
    
    # Collect replay packs from replays directory
    REPLAYS_DIR = Path("replays")
    replays = []
    if REPLAYS_DIR.exists():
        for p in sorted(REPLAYS_DIR.glob("replay_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            replays.append((p.name, p))

    def _li(items: List[Tuple[str, Path]], maxn: int) -> str:
        out = []
        for name, p in items[:maxn]:
            # If path is in replays directory, use relative path from reports
            if "replays" in str(p):
                href = f"../replays/{html.escape(name)}"
            else:
                href = f"./{html.escape(name)}"
            out.append(f"<li><a href='{href}'>{html.escape(name)}</a></li>")
        return "\n".join(out) if out else "<li class='muted'>none</li>"

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:24px}}
h1{{font-size:20px;margin:0 0 12px}}
h2{{font-size:16px;margin:18px 0 6px}}
ul{{margin:0 0 12px 18px}}
.muted{{color:#64748b}}
.small{{font-size:12px;color:#475569}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(2,6,23,.06)}}
</style>
</head>
<body>
  <div class="card">
    <h1>{html.escape(title)}</h1>
    <div class="small">Auto-generated index of recent artifacts.</div>

    <h2>HTML Reports</h2>
    <ul>
      {_li(html_reports, max_items)}
    </ul>

    <h2>CSV — Changes</h2>
    <ul>
      {_li(csvs_changes, max_items)}
    </ul>

    <h2>CSV — Order Previews</h2>
    <ul>
      {_li(csvs_orders, max_items)}
    </ul>

    <h2>Replay Packs</h2>
    <ul>
      {_li(replays, max_items)}
    </ul>

    <div class="small">Tip: refresh to update after each run.</div>
  </div>
</body>
</html>"""
    path = REPORTS_DIR / "index.html"
    path.write_text(doc, encoding="utf-8")
    return path

