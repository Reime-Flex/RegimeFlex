import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.config import Config
from engine.runner import run_daily_offline
from engine.report import write_daily_html
from engine.report_index import build_index
from engine.retention import prune_reports
from engine.checksum import checksum_new_artifacts
from engine.env import load_env
from engine.telemetry import Notifier, TGCreds

if __name__ == "__main__":
    cfg = Config(".")
    run = cfg.run or {}
    tele = cfg.telemetry or {}

    equity = float(run.get("equity", 25_000.0))
    vix = run.get("vix_assumption", 20.0)
    mtc = int(run.get("minutes_to_close", 28))
    min_trade_value = float(run.get("min_trade_value", 200.0))

    RF.print_log(f"Config params: equity={equity}, vix={vix}, mtc={mtc}, min=${min_trade_value}", "INFO")
    result = run_daily_offline(
        equity=equity,
        vix=vix if vix is None or isinstance(vix, (int, float)) else 20.0,
        minutes_to_close=mtc,
        min_trade_value=min_trade_value,
    )

    # HTML report
    rep_cfg = run.get("report", {}) or {}
    if rep_cfg.get("enabled", True):
        out_path = write_daily_html(
            result,
            out_dir=rep_cfg.get("out_dir", "reports"),
            filename_prefix=rep_cfg.get("filename_prefix", "daily_report"),
        )
        RF.print_log(f"HTML report saved → {out_path}", "SUCCESS")

    # Reports index
    idx_cfg = cfg._load_yaml("config/reports.yaml") if (cfg.root / "config/reports.yaml").exists() else {}
    idx_settings = (idx_cfg.get("index") or {})
    try:
        idx_path = build_index(
            max_items=int(idx_settings.get("max_items", 30)),
            title=str(idx_settings.get("title", "RegimeFlex — Reports"))
        )
        RF.print_log(f"Reports index updated → {idx_path}", "SUCCESS")
    except Exception as e:
        RF.print_log(f"Reports index update failed: {e}", "ERROR")

    # Artifact retention
    rep_cfg_full = cfg._load_yaml("config/reports.yaml") if (cfg.root / "config/reports.yaml").exists() else {}
    ret = (rep_cfg_full.get("retention") or {})
    if bool(ret.get("enabled", True)):
        keep = ret.get("keep") or {}
        entries = []
        for _k, spec in keep.items():
            try:
                entries.append((str(spec["pattern"]), int(spec["max"])))
            except Exception:
                continue
        deleted = prune_reports(Path("reports"), entries)
        if deleted:
            RF.print_log(f"Retention: deleted {len(deleted)} old artifact(s).", "INFO")
        else:
            RF.print_log("Retention: nothing to delete.", "INFO")

    # Report integrity checksums
    cs = (rep_cfg_full.get("checksums") or {})
    if bool(cs.get("enabled", True)):
        patterns = [str(x) for x in (cs.get("include_patterns") or [])]
        digests = checksum_new_artifacts(Path("reports"), patterns)
        if digests:
            RF.print_log(f"Checksums written for {len(digests)} artifact(s).", "SUCCESS")
            # Keep the latest report's hash handy in breadcrumbs (optional)
            # Try to pull today's HTML if present; else any one digest
            latest_html = next((k for k in sorted(digests.keys(), reverse=True) if k.endswith(".html")), None)
            if latest_html:
                result["breadcrumbs"] = result.get("breadcrumbs", {})
                result["breadcrumbs"].update({"report_sha256": digests[latest_html]})

    # Optional Telegram (uses Step 20 gating)
    if (cfg.telemetry or {}).get("enabled", True):
        e = load_env()
        notifier = Notifier(TGCreds(token=e.telegram_bot_token, chat_id=e.telegram_chat_id))
        verbosity = (cfg.telemetry or {}).get("verbosity", "brief")
        notifier.send(Notifier.format_run_summary(result, verbosity=verbosity))
    else:
        RF.print_log("Telemetry disabled by telemetry.yaml", "INFO")
