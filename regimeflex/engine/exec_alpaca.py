from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List

from .exec_planner import OrderIntent
from .identity import RegimeFlexIdentity as RF

@dataclass(frozen=True)
class AlpacaCreds:
    key: str | None
    secret: str | None
    base_url: str = "https://paper-api.alpaca.markets"  # default paper URL

def _alpaca_payload(intent: OrderIntent) -> Dict[str, Any]:
    """
    Translate an OrderIntent to Alpaca v2 order payload.
    We use quantity in shares; 'time_in_force' maps to 'day' or 'cls'.
    """
    side = intent.side.lower()        # buy|sell
    tif  = intent.time_in_force.lower()  # day|cls
    payload: Dict[str, Any] = {
        "symbol": intent.symbol,
        "qty": round(float(intent.qty), 6),
        "side": side,
        "time_in_force": "day" if tif == "day" else "cls",
        "type": intent.order_type.lower(),  # limit|market|moc
    }
    if intent.order_type.lower() == "limit":
        payload["limit_price"] = float(intent.limit_price) if intent.limit_price is not None else None
    # For MOC, Alpaca expects type="market" + time_in_force="cls"
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

    def place_orders(self, intents: List[OrderIntent]) -> List[Dict[str, Any]]:
        """
        DRY-RUN: Do not call the API. Just format payloads and return them.
        Later we'll add real POST /v2/orders with requests and auth headers.
        """
        payloads = self.build_payloads(intents)
        for p in payloads:
            RF.print_log(f"[DRY-RUN] Alpaca payload → {p}", "INFO")
        return payloads
