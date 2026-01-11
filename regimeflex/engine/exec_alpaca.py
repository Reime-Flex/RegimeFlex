from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import requests
import os

# Setup Alpaca SDK environment variables at module import
from regimeflex.config.api_keys import APIKeys
APIKeys.setup_alpaca_env()

from regimeflex.engine.exec_planner import OrderIntent
from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.fills_state import append_fill_record
from regimeflex.engine.config import Config
from pathlib import Path

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

    def place_orders(self, intents: List[OrderIntent], mid_prices: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        If dry_run: just format and print payloads.
        Else: POST to /v2/orders for each intent. Returns list of results (payload or API response).
        
        Safety features:
        - Stale data check (validated before calling this)
        - Slippage protection (converts market orders to limit with 0.05% buffer)
        - Duplicate trade prevention (SafetyWrapper lock)
        - Circuit Breaker (Guardian module)
        
        Args:
            intents: List of order intents to execute
            mid_prices: Optional dict of {symbol: mid_price} for slippage protection
        """
        # 1. Import Safety Wrapper
        try:
            from regimeflex.engine.safety_wrapper import SafetyWrapper, OrderLockError
            safety = SafetyWrapper()
        except ImportError:
            safety = None

        payloads = self.build_payloads(intents)
        
        # 2. Apply slippage protection to payloads if mid_prices provided
        if safety and mid_prices:
            protected_payloads = []
            for p in payloads:
                symbol = p.get("symbol", "").upper()
                mid_price = mid_prices.get(symbol)
                if mid_price and mid_price > 0:
                    protected_p = safety.protect_order(p.copy(), mid_price)
                    protected_payloads.append(protected_p)
                else:
                    protected_payloads.append(p)
            payloads = protected_payloads
        
        # ---------------------------------------------------------
        # DRY RUN EXECUTION
        # ---------------------------------------------------------
        if self.dry_run:
            for p in payloads:
                # Shield: Check duplicate prevention even in dry-run
                try:
                    lock_ctx = safety.order_lock(
                        symbol=p.get("symbol", ""),
                        side=p.get("side", "").upper(),
                        qty=p.get("qty", 0.0),
                        limit_price=p.get("limit_price")
                    ) if safety else None
                except Exception:
                    lock_ctx = None

                if lock_ctx:
                    try:
                        with lock_ctx:
                            RF.print_log(f"[DRY-RUN] Would send order: {p}", "RISK")
                            append_fill_record(
                                symbol=p.get("symbol", ""),
                                side=p.get("side", ""),
                                qty=p.get("qty", 0.0),
                                status="sim_accepted",
                                filled_qty=None,
                                broker_id=None
                            )
                    except OrderLockError as e:
                        RF.print_log(f"⛔ DUPLICATE PREVENTED (Dry-Run): {e}", "RISK")
                        continue
                else:
                    # Fallback if safety not loaded
                    RF.print_log(f"[DRY-RUN] Would send order: {p}", "RISK")
                    append_fill_record(
                        symbol=p.get("symbol", ""),
                        side=p.get("side", ""),
                        qty=p.get("qty", 0.0),
                        status="sim_accepted",
                        filled_qty=None,
                        broker_id=None
                    )
            
            return payloads

        # ---------------------------------------------------------
        # LIVE EXECUTION
        # ---------------------------------------------------------
        if not (self.creds.key and self.creds.secret):
            RF.print_log("Alpaca creds missing — refusing to place orders.", "ERROR")
            return []

        results: List[Dict[str, Any]] = []
        url = self.creds.base_url.rstrip("/") + "/v2/orders"
        headers = self._headers()
        
        # Guardian: Get circuit breaker
        try:
            from regimeflex.engine.guardian.circuit_breaker import get_alpaca_breaker, CircuitBreakerError
            breaker = get_alpaca_breaker()
        except ImportError:
            class MockBreaker:
                def execute(self, f): return f()
            breaker = MockBreaker()
            CircuitBreakerError = Exception

        for idx, p in enumerate(payloads):
            # Shield: Apply slippage protection if mid_price available
            if safety and mid_prices:
                symbol = p.get("symbol", "").upper()
                mid_price = mid_prices.get(symbol)
                if mid_price and mid_price > 0:
                    protected_p = safety.protect_order(p.copy(), mid_price)
                    payloads[idx] = protected_p  # Update payload in place
                    RF.print_log(
                        f"🛡️ Slippage protection: {symbol} {p.get('side')} "
                        f"{p.get('type')} → {protected_p.get('type')} @ ${protected_p.get('limit_price', 'N/A')}",
                        "INFO"
                    )
            
            # Shield: Wrap with duplicate prevention lock
            if safety:
                lock_ctx = safety.order_lock(
                    symbol=p.get("symbol", ""),
                    side=p.get("side", "").upper(),
                    qty=p.get("qty", 0.0),
                    limit_price=p.get("limit_price")
                )
            else:
                from contextlib import nullcontext
                lock_ctx = nullcontext()

            try:
                with lock_ctx:
                    RF.print_log(f"[LIVE] POST {url} → {p}", "INFO")
                    
                    # Execute via circuit breaker
                    def _do_post():
                        return requests.post(url, json=p, headers=headers, timeout=30)
                    
                    r = breaker.execute(_do_post)
                    
                    # Priority 2: Enhanced Alpaca Error Handling
                    # Handle specific HTTP status codes with appropriate actions
                    if r.status_code == 429:
                        # Rate limit - log and skip this order, retry next cycle
                        retry_after = r.headers.get("Retry-After", "60")
                        RF.print_log(
                            f"⏸️ Alpaca rate limit (429), retry after {retry_after}s. Order skipped: {p.get('symbol')} {p.get('side')}",
                            "RISK"
                        )
                        results.append({
                            "error": "Rate Limit",
                            "retry_after": retry_after,
                            "status": 429,
                            "request": p,
                            "may_retry": True
                        })
                        continue  # Skip this order, continue with next
                    
                    elif r.status_code in (500, 502, 503, 504):
                        # Server error - order may be queued, log but don't retry immediately
                        RF.print_log(
                            f"⚠️ Alpaca server error ({r.status_code}), order may be queued: {p.get('symbol')} {p.get('side')}",
                            "RISK"
                        )
                        results.append({
                            "error": f"Server Error {r.status_code}",
                            "status": r.status_code,
                            "request": p,
                            "may_retry": True,
                            "response_text": r.text[:200]  # Truncate long responses
                        })
                        continue  # Skip this order
                    
                    elif r.status_code in (401, 403):
                        # Auth error - don't retry, fail immediately
                        RF.print_log(
                            f"🚨 Alpaca authentication error ({r.status_code}): {r.text[:200]}",
                            "ERROR"
                        )
                        results.append({
                            "error": f"Authentication Error {r.status_code}",
                            "status": r.status_code,
                            "request": p,
                            "may_retry": False,
                            "response_text": r.text[:200]
                        })
                        continue  # Skip this order
                    
                    elif r.status_code >= 300:
                        # Other client errors (400, 404, etc.)
                        RF.print_log(
                            f"Alpaca order error {r.status_code}: {r.text[:200]}",
                            "ERROR"
                        )
                        results.append({
                            "error": r.text[:200],
                            "status": r.status_code,
                            "request": p,
                            "may_retry": False
                        })
                    else:
                        # Success (2xx)
                        resp = r.json()
                        results.append(resp)
                        RF.print_log(
                            f"[LIVE] Accepted order id={resp.get('id','?')} status={resp.get('status','?')}",
                            "SUCCESS"
                        )
                        
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
            
            except OrderLockError as e:
                RF.print_log(f"⛔ DUPLICATE PREVENTED: {e}", "ERROR")
                results.append({"error": "Duplicate Order Blocked", "details": str(e), "request": p, "blocked": True})
            except CircuitBreakerError as e:
                RF.print_log(f"Alpaca circuit open: {e}", "RISK")
                results.append({"error": "Circuit Breaker Open", "details": str(e), "request": p})
            except Exception as e:
                RF.print_log(f"Alpaca POST failed: {e}", "ERROR")
                results.append({"error": str(e), "request": p})
                
        return results


def dry_run_details(root: str | Path | None = ".") -> Dict[str, Any]:
    """
    Return a structured view of dry-run state.
    
    Priority:
      1) REGIMEFLEX_DRY_RUN=1 (env)
      2) config/broker.yaml dry_run: true
      3) otherwise false
    """
    root_path = Path(str(root) if root else ".")
    env_val = os.environ.get("REGIMEFLEX_DRY_RUN", "")
    env_flag = (env_val == "1")
    cfg_flag = False
    
    try:
        cfg = Config(root_path)
        broker_cfg = cfg._load_yaml("config/broker.yaml") or {}
        # Check top-level dry_run first, then fall back to alpaca.dry_run
        top_level = broker_cfg.get("dry_run")
        if top_level is not None:
            cfg_flag = bool(top_level)
        else:
            alp = broker_cfg.get("alpaca", {}) or {}
            cfg_flag = bool(alp.get("dry_run", False))
    except FileNotFoundError:
        broker_cfg = {}
        cfg_flag = False
    
    if env_flag:
        return {
            "dry_run": True,
            "source": "env",
            "env_value": env_val,
            "config_value": cfg_flag,
        }
    
    if cfg_flag:
        return {
            "dry_run": True,
            "source": "config",
            "env_value": env_val,
            "config_value": cfg_flag,
        }
    
    return {
        "dry_run": False,
        "source": "none",
        "env_value": env_val,
        "config_value": cfg_flag,
    }


def is_dry_run(root: str | Path | None = ".") -> bool:
    """
    Dry-run is true if either:
      - ENV REGIMEFLEX_DRY_RUN=1, OR
      - config/broker.yaml has dry_run: true (top-level or alpaca.dry_run)
    
    Returns True if dry-run mode should be active.
    """
    return dry_run_details(root).get("dry_run", False)


def place_order(api_or_executor, order: Dict[str, Any], root: str | Path | None = ".") -> Dict[str, Any]:
    """
    Unified order entry point. If dry-run is active:
      - logs the order
      - does NOT send to Alpaca
    Otherwise:
      - forwards to AlpacaExecutor.place_orders() or makes API call.
    
    This is a convenience wrapper that ensures all order submissions
    respect the dry-run flag via is_dry_run().
    
    Note: The existing AlpacaExecutor.place_orders() already handles dry_run
    via the executor's dry_run flag, but this function provides an additional
    gate that checks is_dry_run() for extra safety.
    """
    if is_dry_run(root):
        RF.print_log(f"[DRY-RUN] Would send order: {order}", "RISK")
        return {"dry_run": True, "order": order}
    
    # If it's an AlpacaExecutor instance, use its place_orders method
    if isinstance(api_or_executor, AlpacaExecutor):
        # This shouldn't happen in practice since executor already has dry_run flag,
        # but if called this way, delegate to executor
        intents = [OrderIntent(
            symbol=order["symbol"],
            side=order["side"],
            qty=order["qty"],
            order_type=order.get("type", "market"),
            time_in_force=order.get("time_in_force", "day"),
            limit_price=order.get("limit_price"),
            reason=order.get("reason", "place_order_wrapper")
        )]
        results = api_or_executor.place_orders(intents)
        return results[0] if results else {"error": "No result"}
    
    # Otherwise, this would be a direct API call (not currently used in this codebase)
    RF.print_log(f"Sending live order: {order}", "SIGNAL")
    # Note: Direct API calls are not implemented here as the codebase uses AlpacaExecutor
    return {"error": "Direct API calls not implemented, use AlpacaExecutor"}


def get_alpaca_client_creds() -> AlpacaCreds:
    """
    Get Alpaca credentials using the centralized APIKeys adapter.
    
    This function uses the APIKeys adapter which handles name normalization
    between RegimeFlex's custom names (ALPACA_KEY) and Alpaca SDK's official
    names (APCA_API_KEY_ID).
    """
    key = APIKeys.alpaca_key_id()
    secret = APIKeys.alpaca_secret()
    base_url = APIKeys.alpaca_base_url()
    return AlpacaCreds(key=key, secret=secret, base_url=base_url)


def get_broker_positions() -> Dict[str, float]:
    """
    Return broker positions as {symbol: qty} using Alpaca REST API.
    Long = positive, short = negative, 0 not included.
    """
    creds = get_alpaca_client_creds()
    if not (creds.key and creds.secret):
        raise ValueError("Alpaca credentials not found in environment")
    
    url = creds.base_url.rstrip("/") + "/v2/positions"
    headers = {
        "APCA-API-KEY-ID": creds.key,
        "APCA-API-SECRET-KEY": creds.secret,
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code >= 300:
            raise RuntimeError(f"Alpaca API error {response.status_code}: {response.text}")
        
        positions = response.json()
        out: Dict[str, float] = {}
        
        for p in positions:
            sym = str(p.get("symbol", "")).upper()
            # Alpaca positions API: qty can be string or number, side indicates direction
            qty_raw = p.get("qty", 0.0)
            try:
                qty = float(qty_raw)
            except (ValueError, TypeError):
                continue
            
            # Alpaca positions: side can be "long" or "short"
            # If side is "short", make qty negative
            side = str(p.get("side", "")).lower()
            if side == "short":
                qty = -abs(qty)  # Ensure short positions are negative
            elif side == "long":
                qty = abs(qty)  # Ensure long positions are positive
            
            # Only include non-zero positions
            if abs(qty) > 1e-6:  # Small threshold for floating point
                out[sym] = qty
        
        return out
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch broker positions: {e}") from e
