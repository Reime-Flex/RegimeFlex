"""
Stream Manager

Singleton manager for WebSocket connections and event broadcasting.
Manages Alpaca WebSocket stream and broadcasts updates to subscribers.

Usage:
    from regimeflex.engine.realtime.stream_manager import StreamManager

    manager = StreamManager.get_instance()
    await manager.start()

    # Subscribe to updates
    manager.subscribe(lambda update: print(update))
"""

from __future__ import annotations
import asyncio
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any, List, Set
from queue import Queue, Empty

from regimeflex.engine.identity import RegimeFlexIdentity as RF


@dataclass
class StreamEvent:
    """Event to be broadcast to subscribers."""
    event_type: str  # "trade_update" | "position_update" | "regime_update" | "connection_status"
    data: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StreamManager:
    """
    Singleton manager for WebSocket connections and event broadcasting.

    Manages:
    - Alpaca WebSocket connection for trade updates
    - Subscriber list for event broadcast
    - Event queue for cross-thread communication
    """

    _instance: Optional["StreamManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "StreamManager":
        """Get singleton instance of StreamManager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._stop()
            cls._instance = None

    def __init__(self):
        """Initialize StreamManager (use get_instance() instead)."""
        self._alpaca_stream = None
        self._subscribers: List[Callable[[StreamEvent], None]] = []
        self._event_queue: Queue = Queue()
        self._running = False
        self._stream_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> bool:
        """
        Start streaming connections.

        Returns:
            True if started successfully
        """
        if self._running:
            RF.print_log("[StreamManager] Already running", "INFO")
            return True

        try:
            from regimeflex.engine.realtime.alpaca_stream import (
                AlpacaTradeStream,
                TradeUpdate,
                is_websocket_available,
            )

            if not is_websocket_available():
                RF.print_log("[StreamManager] WebSocket library not available", "RISK")
                return False

            # Get Alpaca credentials
            from regimeflex.engine.exec_alpaca import get_alpaca_client_creds
            creds = get_alpaca_client_creds()

            if not (creds.key and creds.secret):
                RF.print_log("[StreamManager] Alpaca credentials not configured", "ERROR")
                return False

            is_paper = "paper" in creds.base_url.lower()

            # Create stream with callbacks
            self._alpaca_stream = AlpacaTradeStream(
                api_key=creds.key,
                api_secret=creds.secret,
                is_paper=is_paper,
                on_trade_update=self._on_trade_update,
                on_connect=self._on_connect,
                on_disconnect=self._on_disconnect,
            )

            # Connect
            success = await self._alpaca_stream.connect()
            if not success:
                RF.print_log("[StreamManager] Failed to connect to Alpaca stream", "ERROR")
                return False

            self._running = True
            self._loop = asyncio.get_event_loop()

            # Start listen task
            self._stream_task = asyncio.create_task(self._alpaca_stream.listen())

            RF.print_log("[StreamManager] Started successfully", "SUCCESS")
            return True

        except ImportError as e:
            RF.print_log(f"[StreamManager] Import error: {e}", "ERROR")
            return False
        except Exception as e:
            RF.print_log(f"[StreamManager] Start error: {e}", "ERROR")
            return False

    def _stop(self) -> None:
        """Stop all streams (internal method)."""
        self._running = False

        if self._stream_task:
            self._stream_task.cancel()

        if self._alpaca_stream:
            asyncio.create_task(self._alpaca_stream.disconnect())

    async def stop(self) -> None:
        """Stop all streaming connections."""
        RF.print_log("[StreamManager] Stopping...", "INFO")
        self._running = False

        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        if self._alpaca_stream:
            await self._alpaca_stream.disconnect()

        RF.print_log("[StreamManager] Stopped", "INFO")

    def subscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """
        Add subscriber for stream events.

        Args:
            callback: Function to call with each StreamEvent
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            RF.print_log(f"[StreamManager] Added subscriber ({len(self._subscribers)} total)", "INFO")

    def unsubscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """Remove subscriber."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            RF.print_log(f"[StreamManager] Removed subscriber ({len(self._subscribers)} remaining)", "INFO")

    def broadcast(self, event: StreamEvent) -> None:
        """
        Broadcast event to all subscribers.

        Args:
            event: StreamEvent to broadcast
        """
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                RF.print_log(f"[StreamManager] Subscriber error: {e}", "ERROR")

    def queue_event(self, event: StreamEvent) -> None:
        """
        Queue event for broadcast (thread-safe).

        Use this when calling from a non-async context.
        """
        self._event_queue.put(event)

    def get_queued_events(self, max_events: int = 100) -> List[StreamEvent]:
        """
        Get queued events (non-blocking).

        Returns:
            List of queued events
        """
        events = []
        for _ in range(max_events):
            try:
                event = self._event_queue.get_nowait()
                events.append(event)
            except Empty:
                break
        return events

    def _on_trade_update(self, update) -> None:
        """Handle trade update from Alpaca stream."""
        event = StreamEvent(
            event_type="trade_update",
            data=update.to_dict() if hasattr(update, "to_dict") else update,
        )
        self.broadcast(event)

    def _on_connect(self) -> None:
        """Handle WebSocket connect event."""
        event = StreamEvent(
            event_type="connection_status",
            data={"status": "connected", "source": "alpaca"},
        )
        self.broadcast(event)

    def _on_disconnect(self, reason: str) -> None:
        """Handle WebSocket disconnect event."""
        event = StreamEvent(
            event_type="connection_status",
            data={"status": "disconnected", "source": "alpaca", "reason": reason},
        )
        self.broadcast(event)

    def broadcast_position_update(self, positions: Dict[str, float]) -> None:
        """Broadcast position update to subscribers."""
        event = StreamEvent(
            event_type="position_update",
            data={"positions": positions},
        )
        self.broadcast(event)

    def broadcast_regime_update(self, regime: str, confidence: float = 0.0) -> None:
        """Broadcast regime update to subscribers."""
        event = StreamEvent(
            event_type="regime_update",
            data={"regime": regime, "confidence": confidence},
        )
        self.broadcast(event)

    @property
    def is_running(self) -> bool:
        """Check if StreamManager is running."""
        return self._running

    @property
    def is_connected(self) -> bool:
        """Check if Alpaca stream is connected."""
        if self._alpaca_stream:
            return self._alpaca_stream.is_connected
        return False

    @property
    def subscriber_count(self) -> int:
        """Get number of subscribers."""
        return len(self._subscribers)


# Background thread runner for non-async contexts
def start_stream_background() -> threading.Thread:
    """
    Start StreamManager in a background thread.

    Returns:
        Thread running the event loop
    """
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        manager = StreamManager.get_instance()
        manager._loop = loop

        try:
            loop.run_until_complete(manager.start())
            loop.run_forever()
        except Exception as e:
            RF.print_log(f"[StreamManager] Background thread error: {e}", "ERROR")
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="StreamManager")
    thread.start()

    RF.print_log("[StreamManager] Started background thread", "INFO")
    return thread
