import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.storage import ENSStyleAudit

if __name__ == "__main__":
    audit = ENSStyleAudit()
    RF.print_log("Writing a demo PLAN record to the audit ledger…", "INFO")

    demo = {
        "symbol": "QQQ",
        "side": "BUY",
        "qty": 12.34,
        "order_type": "limit",
        "time_in_force": "day",
        "limit_price": 395.25,
        "reason": "demo plan for audit"
    }
    rec = audit.log(kind="PLAN", data=demo)

    RF.print_log(f"Audit TX → {rec.tx_hash} @ {rec.timestamp} (block {rec.block})", "SUCCESS")
    RF.print_log("Open logs/audit/ to see the JSONL file.", "INFO")
