"""
Order Transaction Manager

Provides transactional boundaries for order execution with proper WAL integration.
Ensures orders are either fully completed or rolled back on failure.

Usage:
    from regimeflex.engine.order_transaction import TransactionalOrderManager

    txn_manager = TransactionalOrderManager()

    for intent in intents:
        with txn_manager.transaction(intent) as txn:
            result = executor.submit_order(intent)
            txn.mark_submitted(result['id'])
            txn.mark_acknowledged(result)
            # If exception occurs before this point, auto-rollback
"""

from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Generator
import uuid

from regimeflex.engine.exec_planner import OrderIntent
from regimeflex.engine.order_wal import (
    log_intent,
    log_submitted,
    log_acknowledged,
    log_filled,
    log_failed,
    log_rolled_back,
    get_pending_orders,
    WALEntry,
)
from regimeflex.engine.identity import RegimeFlexIdentity as RF


@dataclass
class OrderTransaction:
    """
    Represents an in-flight order transaction.

    Tracks the order through its lifecycle phases:
    INTENT -> SUBMITTED -> ACKNOWLEDGED -> FILLED

    On failure, transitions to ROLLED_BACK or FAILED.
    """
    intent_id: str
    intent: OrderIntent
    phase: str  # INTENT | SUBMITTED | ACKNOWLEDGED | FILLED | ROLLED_BACK | FAILED
    created_at: datetime
    broker_order_id: Optional[str] = None
    fill_price: Optional[float] = None
    filled_qty: Optional[float] = None
    error: Optional[str] = None
    broker_response: Optional[Dict[str, Any]] = None

    def mark_submitted(self, broker_order_id: str) -> None:
        """Mark order as submitted to broker."""
        self.broker_order_id = broker_order_id
        self.phase = "SUBMITTED"
        log_submitted(self.intent_id, broker_order_id)
        RF.print_log(f"[TXN] Order {self.intent_id} submitted -> broker_id={broker_order_id}", "INFO")

    def mark_acknowledged(self, broker_response: Dict[str, Any]) -> None:
        """Mark order as acknowledged by broker."""
        self.broker_response = broker_response
        self.phase = "ACKNOWLEDGED"
        log_acknowledged(self.intent_id, broker_response)

        # Extract broker order ID if not already set
        if not self.broker_order_id:
            self.broker_order_id = broker_response.get("id")

        RF.print_log(f"[TXN] Order {self.intent_id} acknowledged", "INFO")

    def mark_filled(self, filled_qty: float, fill_price: float) -> None:
        """Mark order as filled."""
        self.filled_qty = filled_qty
        self.fill_price = fill_price
        self.phase = "FILLED"
        log_filled(self.intent_id, filled_qty, fill_price)
        RF.print_log(f"[TXN] Order {self.intent_id} filled: {filled_qty} @ ${fill_price}", "SUCCESS")

    def to_result(self) -> Dict[str, Any]:
        """Convert transaction to result dict for return from place_orders."""
        return {
            "intent_id": self.intent_id,
            "symbol": self.intent.symbol,
            "side": self.intent.side,
            "qty": self.intent.qty,
            "phase": self.phase,
            "broker_order_id": self.broker_order_id,
            "broker_response": self.broker_response,
            "error": self.error,
            "fill_price": self.fill_price,
            "filled_qty": self.filled_qty,
        }


class TransactionalOrderManager:
    """
    Manages order execution within transactional boundaries.

    Provides:
    - Automatic WAL logging at each phase
    - Automatic rollback on exception
    - Recovery of pending orders on startup
    """

    def __init__(self):
        pass

    def _generate_intent_id(self, intent: OrderIntent) -> str:
        """Generate unique intent ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{intent.symbol}_{intent.side}_{ts}_{short_uuid}"

    @contextmanager
    def transaction(self, intent: OrderIntent) -> Generator[OrderTransaction, None, None]:
        """
        Transactional boundary for order execution.

        Usage:
            with manager.transaction(intent) as txn:
                result = executor.submit_order(intent)
                txn.mark_submitted(result['id'])
                txn.mark_acknowledged(result)
                # Optionally mark filled if synchronous fill

        On success:
            - If txn reaches ACKNOWLEDGED phase, marks as FILLED automatically
              (assuming market orders fill immediately)

        On exception:
            - Logs ROLLED_BACK phase to WAL
            - Sets txn.error with exception message
            - Re-raises exception
        """
        intent_id = self._generate_intent_id(intent)
        txn = OrderTransaction(
            intent_id=intent_id,
            intent=intent,
            phase="INTENT",
            created_at=datetime.now(timezone.utc)
        )

        # Phase 1: Log INTENT to WAL
        log_intent(intent_id, intent.symbol, intent.side, intent.qty)
        RF.print_log(f"[TXN] Started transaction {intent_id} for {intent.symbol} {intent.side} {intent.qty}", "INFO")

        try:
            yield txn

            # Transaction completed without exception
            # If we reached ACKNOWLEDGED but not FILLED, auto-fill for market orders
            if txn.phase == "ACKNOWLEDGED" and txn.phase != "FILLED":
                # For market orders, assume immediate fill at limit price or 0
                fill_price = txn.broker_response.get("filled_avg_price", 0.0) if txn.broker_response else 0.0
                if fill_price == 0.0 and intent.limit_price:
                    fill_price = intent.limit_price

                filled_qty = txn.broker_response.get("filled_qty", intent.qty) if txn.broker_response else intent.qty
                txn.mark_filled(float(filled_qty), float(fill_price))

            RF.print_log(f"[TXN] Completed transaction {intent_id} in phase {txn.phase}", "SUCCESS")

        except Exception as e:
            # Rollback: Log failure to WAL
            error_msg = str(e)
            txn.phase = "ROLLED_BACK"
            txn.error = error_msg

            log_rolled_back(intent_id, error_msg)
            RF.print_log(f"[TXN] Rolled back transaction {intent_id}: {error_msg}", "ERROR")

            raise

    def recover_pending(self) -> List[OrderTransaction]:
        """
        Recover transactions that were SUBMITTED or ACKNOWLEDGED but not FILLED.

        Call this on startup to identify orders that may need manual reconciliation.

        Returns:
            List of OrderTransaction objects in pending state
        """
        pending_entries = get_pending_orders()

        transactions = []
        for entry in pending_entries:
            # Reconstruct minimal OrderIntent
            intent = OrderIntent(
                symbol=entry.symbol,
                side=entry.side,
                qty=entry.qty,
                order_type="unknown",
                time_in_force="day",
                limit_price=None,
                reason="recovered_from_wal"
            )

            txn = OrderTransaction(
                intent_id=entry.id,
                intent=intent,
                phase=entry.phase,
                created_at=datetime.fromisoformat(entry.timestamp) if entry.timestamp else datetime.now(timezone.utc),
                broker_order_id=entry.order_id,
                broker_response=entry.details,
            )
            transactions.append(txn)

        if transactions:
            RF.print_log(f"[TXN] Recovered {len(transactions)} pending transactions from WAL", "RISK")

        return transactions

    def get_transaction_status(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a transaction by intent ID.

        Reads WAL to find the latest phase for the given intent ID.
        """
        from regimeflex.config.paths import ORDER_WAL_FILE
        import json

        if not ORDER_WAL_FILE.exists():
            return None

        latest_entry = None
        with ORDER_WAL_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("id") == intent_id:
                        latest_entry = data
                except Exception:
                    continue

        return latest_entry
