from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import requests

from .exec_planner import OrderIntent
from .identity import RegimeFlexIdentity as RF
from .fills_state import append_fill_record

ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_URL  = "https://api.alpaca.markets"

@dataclass(frozen=True)
class AlpacaCreds:
    key: Optional[str]
    secret: Optional[str]
    base_url: str = ALPACA_PAPER_URL  # paper by default

def _alpaca_payload(intent: OrderIntent) -> Dict[str, Any]:
    side = intent.side.lower()        # buy|sell
    tif  = intent.time_in_force.lower()
    payload: Dict[str, Any] = {
        "symbol": intent.symbol,
        "qty": round(float(intent.qty), 6),
        "side": side,
        "time_in_force": "day" if tif == "day" else "cls",
        "type": intent.order_type.lower(),
    }
    if intent.order_type.lower() == "limit":
        payload["limit_price"] = float(intent.limit_price) if intent.limit_price is not None else None
    # MOC on Alpaca = market + time_in_force=cls
    if intent.order_type.lower() == "moc":
        payload["type"] = "market"
        payload["time_in_force"] = "cls"
    return payload

class AlpacaExecutor:
    def __init__(self, creds: AlpacaCreds, dry_run: bool = True):
        self.creds = creds
        self.dry_run = dry_run

    def build_payloads(self, intents: List[OrderIntent]) -> List[Dict[str, Any]]:
        return [_alpaca_payload(it) for it in intents]

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.creds.key or "",
            "APCA-API-SECRET-KEY": self.creds.secret or "",
            "Content-Type": "application/json"
        }

    def place_orders(self, intents: List[OrderIntent]) -> List[Dict[str, Any]]:
        """
        If dry_run: just format and print payloads.
        Else: POST to /v2/orders for each intent. Returns list of results (payload or API response).
        """
        payloads = self.build_payloads(intents)

        if self.dry_run:
            for p in payloads:
                RF.print_log(f"[DRY-RUN] Alpaca payload → {p}", "INFO")
                # Record dry-run fill
                append_fill_record(
                    symbol=p.get("symbol", ""),
                    side=p.get("side", ""),
                    qty=p.get("qty", 0.0),
                    status="sim_accepted",
                    filled_qty=None,
                    broker_id=None
                )
            return payloads

        # Safety: require creds
        if not (self.creds.key and self.creds.secret):
            RF.print_log("Alpaca creds missing — refusing to place orders.", "ERROR")
            return []

        results: List[Dict[str, Any]] = []
        url = self.creds.base_url.rstrip("/") + "/v2/orders"
        headers = self._headers()

        for p in payloads:
            try:
                RF.print_log(f"[LIVE] POST {url} → {p}", "INFO")
                r = requests.post(url, json=p, headers=headers, timeout=30)
                if r.status_code >= 300:
                    RF.print_log(f"Alpaca order error {r.status_code}: {r.text}", "ERROR")
                    results.append({"error": r.text, "status": r.status_code, "request": p})
                else:
                    resp = r.json()
                    results.append(resp)
                    RF.print_log(f"[LIVE] Accepted order id={resp.get('id','?')} status={resp.get('status','?')}", "SUCCESS")
                    
                    # Record live fill
                    status = str(resp.get("status") or resp.get("response","")).lower()
                    filled = resp.get("filled_qty") or resp.get("filled_qty_amount") or resp.get("request",{}).get("qty_filled")
                    append_fill_record(
                        symbol=p.get("symbol", ""),
                        side=p.get("side", ""),
                        qty=p.get("qty", 0.0),
                        status=status,
                        filled_qty=filled,
                        broker_id=resp.get("id")
                    )
            except Exception as e:
                RF.print_log(f"Alpaca POST failed: {e}", "ERROR")
                results.append({"error": str(e), "request": p})
        return results
