"""
Fill Reconciliation Module

Reconciles local fill state with broker (Alpaca) on startup to ensure
position consistency and detect any discrepancies.

Usage:
    from regimeflex.engine.fill_reconciliation import FillReconciler

    reconciler = FillReconciler()
    result = reconciler.reconcile_on_startup()

    if result.status == "DISCREPANCY_ALERT":
        # Handle alert
        pass
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import requests

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.positions import load_positions, save_positions
from regimeflex.engine.exec_alpaca import get_alpaca_client_creds, get_broker_positions
from regimeflex.config.paths import FILLS_STATE_FILE


@dataclass
class ReconciliationResult:
    """Result of fill reconciliation."""
    status: str  # "CLEAN" | "ADJUSTED" | "DISCREPANCY_ALERT"
    local_fills: List[Dict[str, Any]] = field(default_factory=list)
    broker_fills: List[Dict[str, Any]] = field(default_factory=list)
    adjustments: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    local_positions: Dict[str, float] = field(default_factory=dict)
    broker_positions: Dict[str, float] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class FillReconciler:
    """
    Reconciles local fill state with broker data.

    Performs the following on startup:
    1. Query Alpaca for today's fills via account activities
    2. Compare with local fills_state.jsonl
    3. Update positions.json to match broker state
    4. Return any discrepancies for alerting
    """

    def __init__(self, fills_path: Optional[Path] = None):
        self.fills_path = fills_path or FILLS_STATE_FILE

    def reconcile_on_startup(self) -> ReconciliationResult:
        """
        Full reconciliation sequence.

        Returns:
            ReconciliationResult with status and any adjustments made
        """
        result = ReconciliationResult(status="CLEAN")
        RF.print_log("[RECONCILE] Starting fill reconciliation...", "INFO")

        try:
            # Step 1: Get broker data
            broker_fills = self._fetch_broker_fills_today()
            result.broker_fills = broker_fills
            RF.print_log(f"[RECONCILE] Fetched {len(broker_fills)} broker fills for today", "INFO")

            broker_positions = self._fetch_broker_positions()
            result.broker_positions = broker_positions
            RF.print_log(f"[RECONCILE] Broker positions: {broker_positions}", "INFO")

            # Step 2: Get local data
            local_fills = self._read_local_fills_today()
            result.local_fills = local_fills
            RF.print_log(f"[RECONCILE] Found {len(local_fills)} local fills for today", "INFO")

            local_positions = load_positions()
            result.local_positions = local_positions
            RF.print_log(f"[RECONCILE] Local positions: {local_positions}", "INFO")

            # Step 3: Compare fills
            missing_fills, extra_fills = self._compare_fills(local_fills, broker_fills)

            if missing_fills:
                RF.print_log(f"[RECONCILE] Found {len(missing_fills)} missing fills (in broker but not local)", "RISK")
                for fill in missing_fills:
                    self._append_missing_fill(fill)
                    result.adjustments.append({
                        "type": "missing_fill_added",
                        "fill": fill
                    })
                result.status = "ADJUSTED"

            if extra_fills:
                # Fills in local but not broker - could be stale or test data
                RF.print_log(f"[RECONCILE] Found {len(extra_fills)} extra local fills (not in broker)", "RISK")
                for fill in extra_fills:
                    result.alerts.append(f"Local fill not in broker: {fill.get('symbol')} {fill.get('side')} {fill.get('qty')}")

            # Step 4: Compare positions
            position_drift = self._calculate_position_drift(local_positions, broker_positions)

            if position_drift:
                RF.print_log(f"[RECONCILE] Position drift detected: {position_drift}", "RISK")

                # Trust broker positions as source of truth
                save_positions(broker_positions)
                result.adjustments.append({
                    "type": "position_sync",
                    "from": local_positions,
                    "to": broker_positions,
                    "drift": position_drift
                })
                result.status = "ADJUSTED"

                # Add alerts for significant drift
                for sym, drift in position_drift.items():
                    if abs(drift) > 0.5:  # More than 0.5 shares drift
                        result.alerts.append(
                            f"Position drift {sym}: local={local_positions.get(sym, 0)}, "
                            f"broker={broker_positions.get(sym, 0)}, drift={drift}"
                        )

            # Step 5: Check for partial fills
            partial_fills = self._find_partial_fills(broker_fills)
            if partial_fills:
                for partial in partial_fills:
                    result.alerts.append(
                        f"Partial fill: {partial.get('symbol')} filled {partial.get('filled_qty')}/{partial.get('qty')}"
                    )

            # Upgrade status if there are alerts
            if result.alerts and result.status != "ADJUSTED":
                result.status = "DISCREPANCY_ALERT"
            elif result.alerts:
                result.status = "DISCREPANCY_ALERT"

            RF.print_log(f"[RECONCILE] Completed with status: {result.status}", "SUCCESS")

        except Exception as e:
            RF.print_log(f"[RECONCILE] Error during reconciliation: {e}", "ERROR")
            result.status = "DISCREPANCY_ALERT"
            result.alerts.append(f"Reconciliation error: {str(e)}")

        return result

    def _fetch_broker_fills_today(self) -> List[Dict[str, Any]]:
        """Query Alpaca for today's fills via account activities endpoint."""
        creds = get_alpaca_client_creds()
        if not (creds.key and creds.secret):
            RF.print_log("[RECONCILE] No Alpaca credentials, skipping broker fills fetch", "RISK")
            return []

        url = f"{creds.base_url.rstrip('/')}/v2/account/activities"
        headers = {
            "APCA-API-KEY-ID": creds.key,
            "APCA-API-SECRET-KEY": creds.secret,
        }

        # Get today's date in ISO format
        today = date.today().isoformat()

        params = {
            "activity_types": "FILL",
            "after": f"{today}T00:00:00Z",
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code != 200:
                RF.print_log(f"[RECONCILE] Alpaca activities API error: {response.status_code}", "ERROR")
                return []

            activities = response.json()

            fills = []
            for activity in activities:
                if activity.get("activity_type") == "FILL":
                    fills.append({
                        "broker_id": activity.get("id"),
                        "order_id": activity.get("order_id"),
                        "symbol": activity.get("symbol", "").upper(),
                        "side": activity.get("side", "").lower(),
                        "qty": float(activity.get("qty", 0)),
                        "price": float(activity.get("price", 0)),
                        "timestamp": activity.get("transaction_time"),
                        "type": activity.get("type"),  # "fill" or "partial_fill"
                    })

            return fills

        except Exception as e:
            RF.print_log(f"[RECONCILE] Error fetching broker fills: {e}", "ERROR")
            return []

    def _fetch_broker_positions(self) -> Dict[str, float]:
        """Fetch current positions from broker."""
        try:
            return get_broker_positions()
        except Exception as e:
            RF.print_log(f"[RECONCILE] Error fetching broker positions: {e}", "ERROR")
            return {}

    def _read_local_fills_today(self) -> List[Dict[str, Any]]:
        """Read today's fills from local fills_state.jsonl."""
        if not self.fills_path.exists():
            return []

        today_str = date.today().isoformat()
        fills = []

        try:
            with self.fills_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        fill = json.loads(line)
                        # Check if fill is from today
                        ts = fill.get("ts", "")
                        if ts.startswith(today_str):
                            fills.append(fill)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            RF.print_log(f"[RECONCILE] Error reading local fills: {e}", "ERROR")

        return fills

    def _compare_fills(
        self,
        local_fills: List[Dict[str, Any]],
        broker_fills: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Compare local and broker fills.

        Returns:
            (missing_fills, extra_fills)
            - missing_fills: In broker but not local
            - extra_fills: In local but not broker
        """
        # Create sets for comparison based on broker_id
        local_broker_ids = {f.get("broker_id") for f in local_fills if f.get("broker_id")}
        broker_order_ids = {f.get("order_id") for f in broker_fills}

        # Find fills in broker but not local
        missing_fills = [
            f for f in broker_fills
            if f.get("order_id") and f.get("order_id") not in local_broker_ids
        ]

        # Find fills in local but not broker (by order_id)
        extra_fills = [
            f for f in local_fills
            if f.get("broker_id") and f.get("broker_id") not in broker_order_ids
        ]

        return missing_fills, extra_fills

    def _calculate_position_drift(
        self,
        local_positions: Dict[str, float],
        broker_positions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate drift between local and broker positions.

        Returns:
            Dict of {symbol: drift} where drift = broker - local
        """
        drift = {}
        all_symbols = set(local_positions.keys()) | set(broker_positions.keys())

        for sym in all_symbols:
            local = local_positions.get(sym, 0.0)
            broker = broker_positions.get(sym, 0.0)
            diff = broker - local

            if abs(diff) > 1e-6:  # Ignore tiny floating point differences
                drift[sym] = diff

        return drift

    def _append_missing_fill(self, fill: Dict[str, Any]) -> None:
        """Append a missing fill to the local fills_state file."""
        from regimeflex.engine.fills_state import append_fill_record

        append_fill_record(
            symbol=fill.get("symbol", ""),
            side=fill.get("side", ""),
            qty=fill.get("qty", 0),
            status="reconciled_from_broker",
            filled_qty=fill.get("qty"),
            broker_id=fill.get("order_id"),
        )

    def _find_partial_fills(self, broker_fills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find any partial fills in broker data."""
        return [f for f in broker_fills if f.get("type") == "partial_fill"]


def get_broker_fills(
    start_date: date,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Fetch fills from Alpaca for a date range.

    Args:
        start_date: Start date for fills query
        end_date: End date (optional, defaults to today)

    Returns:
        List of fill records from Alpaca
    """
    creds = get_alpaca_client_creds()
    if not (creds.key and creds.secret):
        raise ValueError("Alpaca credentials not configured")

    url = f"{creds.base_url.rstrip('/')}/v2/account/activities"
    headers = {
        "APCA-API-KEY-ID": creds.key,
        "APCA-API-SECRET-KEY": creds.secret,
    }

    params = {
        "activity_types": "FILL",
        "after": f"{start_date.isoformat()}T00:00:00Z",
    }

    if end_date:
        params["until"] = f"{end_date.isoformat()}T23:59:59Z"

    response = requests.get(url, headers=headers, params=params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Alpaca API error {response.status_code}: {response.text}")

    activities = response.json()

    fills = []
    for activity in activities:
        if activity.get("activity_type") == "FILL":
            fills.append({
                "broker_id": activity.get("id"),
                "order_id": activity.get("order_id"),
                "symbol": activity.get("symbol", "").upper(),
                "side": activity.get("side", "").lower(),
                "qty": float(activity.get("qty", 0)),
                "price": float(activity.get("price", 0)),
                "timestamp": activity.get("transaction_time"),
                "type": activity.get("type"),
                "cumulative_qty": float(activity.get("cumulative_qty", 0)),
                "leaves_qty": float(activity.get("leaves_qty", 0)),
            })

    return fills
