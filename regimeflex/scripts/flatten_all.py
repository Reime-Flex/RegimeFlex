
import sys
import requests
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.exec_alpaca import get_alpaca_client_creds

def flatten_all():
    """
    EMERGENCY SCRIPT: LIQUIDATES ALL POSITIONS
    Uses Alpaca's DELETE /v2/positions endpoint.
    """
    RF.print_log("⚠️  INITIATING EMERGENCY FLATTEN ALL  ⚠️", "RISK")
    
    try:
        creds = get_alpaca_client_creds()
        if not creds.key:
            RF.print_log("No API Keys found!", "ERROR")
            return

        url = creds.base_url.rstrip("/") + "/v2/positions"
        headers = {
            "APCA-API-KEY-ID": creds.key,
            "APCA-API-SECRET-KEY": creds.secret,
        }
        
        RF.print_log(f"Sending DELETE to {url}...", "INFO")
        response = requests.delete(url, headers=headers, params={"cancel_orders": "true"}, timeout=10)
        
        if response.status_code in [200, 207]:
            # 207 Multi-Status is returned if some orders fail, but the request was processed
            RF.print_log("✅ Flatten signal accepted by broker.", "SUCCESS")
            for item in response.json():
                symbol = item.get("symbol")
                status = item.get("status")
                RF.print_log(f"   -> {symbol}: {status}", "INFO" if status == 200 else "ERROR")
        else:
            RF.print_log(f"❌ Failed to flatten: {response.text}", "ERROR")

    except Exception as e:
        RF.print_log(f"❌ CRITICAL ERROR executing flatten: {e}", "ERROR")

if __name__ == "__main__":
    confirm = input("Are you sure you want to FLATTEN ALL POSITIONS? (type 'YES'): ")
    if confirm == "YES":
        flatten_all()
    else:
        print("Aborted.")
