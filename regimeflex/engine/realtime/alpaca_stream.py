"""
Alpaca WebSocket Trade Stream

Provides real-time trade updates (fills, cancellations, rejections) via WebSocket
connection to Alpaca's streaming API.

Usage:
    from regimeflex.engine.realtime.alpaca_stream import AlpacaTradeStream

    async def on_fill(update):
        print(f"Fill received: {update}")

    stream = AlpacaTradeStream(
        api_key="...",
        api_secret="...",
        on_trade_update=on_fill
    )

    await stream.connect()
    await stream.listen()
"""

from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any, List
import logging

# WebSocket library - install with: pip install websockets
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None

from regimeflex.engine.identity import RegimeFlexIdentity as RF


@dataclass
class TradeUpdate:
    """Represents a trade update event from Alpaca."""
    event: str  # "fill" | "partial_fill" | "canceled" | "rejected" | "new" | "replaced"
    order_id: str
    symbol: str
    qty: float
    filled_qty: float
    price: float
    timestamp: str
    side: str = ""
    order_type: str = ""
    time_in_force: str = ""
    client_order_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlpacaTradeStream:
    """
    WebSocket connection to Alpaca for real-time trade updates.

    Connects to:
    - Paper: wss://paper-api.alpaca.markets/stream
    - Live: wss://api.alpaca.markets/stream
    """

    WS_PAPER = "wss://paper-api.alpaca.markets/stream"
    WS_LIVE = "wss://api.alpaca.markets/stream"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        is_paper: bool = True,
        on_trade_update: Optional[Callable[[TradeUpdate], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[str], None]] = None,
        reconnect_delay: float = 5.0,
        heartbeat_interval: float = 30.0,
    ):
        """
        Initialize Alpaca WebSocket stream.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            is_paper: True for paper trading, False for live
            on_trade_update: Callback for trade update events
            on_connect: Callback when connected
            on_disconnect: Callback when disconnected
            reconnect_delay: Seconds to wait before reconnecting
            heartbeat_interval: Seconds between heartbeat/ping
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets library not installed. Run: pip install websockets")

        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = self.WS_PAPER if is_paper else self.WS_LIVE
        self.on_trade_update = on_trade_update
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.reconnect_delay = reconnect_delay
        self.heartbeat_interval = heartbeat_interval

        self._running = False
        self._ws: Optional[WebSocketClientProtocol] = None
        self._authenticated = False
        self._reconnect_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """
        Establish WebSocket connection and authenticate.

        Returns:
            True if connection and authentication successful
        """
        try:
            RF.print_log(f"[WS] Connecting to {self.ws_url}...", "INFO")
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=self.heartbeat_interval,
                ping_timeout=10.0,
            )

            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": self.api_key,
                "secret": self.api_secret
            }
            await self._ws.send(json.dumps(auth_msg))

            # Wait for auth response
            response = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            data = json.loads(response)

            if self._is_auth_success(data):
                self._authenticated = True
                RF.print_log("[WS] Authenticated successfully", "SUCCESS")

                # Subscribe to trade updates
                subscribe_msg = {
                    "action": "listen",
                    "data": {"streams": ["trade_updates"]}
                }
                await self._ws.send(json.dumps(subscribe_msg))

                self._running = True

                if self.on_connect:
                    self.on_connect()

                return True
            else:
                RF.print_log(f"[WS] Authentication failed: {data}", "ERROR")
                return False

        except Exception as e:
            RF.print_log(f"[WS] Connection error: {e}", "ERROR")
            return False

    def _is_auth_success(self, data: Dict[str, Any]) -> bool:
        """Check if auth response indicates success."""
        # Alpaca WebSocket auth response format
        if isinstance(data, list):
            for item in data:
                if item.get("T") == "success" and item.get("msg") == "authenticated":
                    return True
        elif isinstance(data, dict):
            if data.get("stream") == "authorization" and data.get("data", {}).get("status") == "authorized":
                return True
            if data.get("T") == "success":
                return True
        return False

    async def listen(self) -> None:
        """
        Main event loop for receiving and processing updates.

        Call this after connect() to start receiving events.
        """
        if not self._ws or not self._authenticated:
            RF.print_log("[WS] Not connected or authenticated, cannot listen", "ERROR")
            return

        RF.print_log("[WS] Starting listen loop...", "INFO")

        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=self.heartbeat_interval + 5.0
                )
                await self._handle_message(message)

            except asyncio.TimeoutError:
                # No message received, send ping to keep connection alive
                try:
                    pong = await self._ws.ping()
                    await asyncio.wait_for(pong, timeout=5.0)
                except Exception:
                    RF.print_log("[WS] Ping failed, connection may be dead", "RISK")
                    await self._reconnect()

            except websockets.exceptions.ConnectionClosed as e:
                RF.print_log(f"[WS] Connection closed: {e}", "RISK")
                if self.on_disconnect:
                    self.on_disconnect(str(e))
                await self._reconnect()

            except Exception as e:
                RF.print_log(f"[WS] Error in listen loop: {e}", "ERROR")
                await asyncio.sleep(1.0)

    async def _handle_message(self, raw_message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            data = json.loads(raw_message)

            # Handle array of messages
            if isinstance(data, list):
                for item in data:
                    await self._process_item(item)
            else:
                await self._process_item(data)

        except json.JSONDecodeError as e:
            RF.print_log(f"[WS] Invalid JSON: {e}", "ERROR")

    async def _process_item(self, item: Dict[str, Any]) -> None:
        """Process a single message item."""
        msg_type = item.get("T") or item.get("stream")

        if msg_type == "trade_updates" or item.get("stream") == "trade_updates":
            update_data = item.get("data", item)
            await self._handle_trade_update(update_data)

        elif msg_type == "success":
            # Subscription confirmation
            RF.print_log(f"[WS] Subscription confirmed: {item.get('msg', '')}", "INFO")

        elif msg_type == "error":
            RF.print_log(f"[WS] Error message: {item}", "ERROR")

    async def _handle_trade_update(self, data: Dict[str, Any]) -> None:
        """Handle trade update event."""
        event = data.get("event", "")
        order = data.get("order", {})

        trade_update = TradeUpdate(
            event=event,
            order_id=order.get("id", ""),
            symbol=order.get("symbol", "").upper(),
            qty=float(order.get("qty", 0)),
            filled_qty=float(order.get("filled_qty", 0)),
            price=float(data.get("price", 0)) or float(order.get("filled_avg_price", 0)),
            timestamp=data.get("timestamp", "") or order.get("updated_at", ""),
            side=order.get("side", ""),
            order_type=order.get("type", ""),
            time_in_force=order.get("time_in_force", ""),
            client_order_id=order.get("client_order_id", ""),
        )

        RF.print_log(
            f"[WS] Trade update: {event} {trade_update.symbol} "
            f"{trade_update.filled_qty}/{trade_update.qty} @ ${trade_update.price}",
            "INFO"
        )

        # Record to WAL if it's a fill event
        if event in ("fill", "partial_fill"):
            await self._record_fill(trade_update)

        # Call user callback
        if self.on_trade_update:
            try:
                self.on_trade_update(trade_update)
            except Exception as e:
                RF.print_log(f"[WS] Callback error: {e}", "ERROR")

    async def _record_fill(self, update: TradeUpdate) -> None:
        """Record fill to WAL and fills_state."""
        try:
            from regimeflex.engine.order_wal import log_filled
            from regimeflex.engine.fills_state import append_fill_record

            # Update WAL
            log_filled(update.order_id, update.filled_qty, update.price)

            # Update fills_state
            append_fill_record(
                symbol=update.symbol,
                side=update.side,
                qty=update.qty,
                status=update.event,
                filled_qty=update.filled_qty,
                broker_id=update.order_id,
            )

            RF.print_log(f"[WS] Recorded fill: {update.symbol} {update.event}", "SUCCESS")

        except Exception as e:
            RF.print_log(f"[WS] Error recording fill: {e}", "ERROR")

    async def _reconnect(self) -> None:
        """Attempt to reconnect after connection loss."""
        self._running = False
        self._authenticated = False

        RF.print_log(f"[WS] Reconnecting in {self.reconnect_delay}s...", "RISK")
        await asyncio.sleep(self.reconnect_delay)

        success = await self.connect()
        if success:
            RF.print_log("[WS] Reconnected successfully", "SUCCESS")
            # Resume listening in background
            self._reconnect_task = asyncio.create_task(self.listen())
        else:
            RF.print_log("[WS] Reconnection failed, will retry...", "ERROR")
            await self._reconnect()

    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket."""
        self._running = False

        if self._ws:
            try:
                await self._ws.close()
                RF.print_log("[WS] Disconnected", "INFO")
            except Exception as e:
                RF.print_log(f"[WS] Error disconnecting: {e}", "ERROR")

        self._ws = None
        self._authenticated = False

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and authenticated."""
        return self._running and self._authenticated and self._ws is not None


# Convenience function to check WebSocket availability
def is_websocket_available() -> bool:
    """Check if websockets library is available."""
    return WEBSOCKETS_AVAILABLE
