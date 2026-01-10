#!/usr/bin/env python
"""
Position Reconciliation Tool
=============================
Compare broker-side positions (Alpaca API) with local state (positions.json)
and flag any discrepancies.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from regimeflex.engine.positions import load_positions
from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.env import load_env
from regimeflex.engine.exec_alpaca import AlpacaCreds, AlpacaExecutor


def fetch_broker_positions(executor: AlpacaExecutor) -> Dict[str, float]:
    """
    Fetch current positions from Alpaca broker.
    
    Args:
        executor: AlpacaExecutor instance
        
    Returns:
        Dict of {symbol: shares}
    """
    import requests
    
    broker_pos = {}
    
    try:
        # Get positions from Alpaca API
        url = executor.creds.base_url.rstrip("/") + "/v2/positions"
        headers = executor._headers()
        
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            positions = r.json()
            for pos in positions:
                symbol = pos.get("symbol", "").upper()
                qty = float(pos.get("qty", 0.0))
                if abs(qty) > 1e-9:  # Only include non-zero positions
                    broker_pos[symbol] = qty
        else:
            RF.print_log(f"Failed to fetch broker positions: {r.status_code} {r.text[:200]}", "ERROR")
    except Exception as e:
        RF.print_log(f"Error fetching broker positions: {e}", "ERROR")
    
    return broker_pos


def reconcile() -> int:
    """
    Compare broker positions with local state and report discrepancies.
    
    Returns:
        0 if reconciled, 1 if discrepancies found
    """
    local_pos = load_positions()
    
    # Fetch broker positions
    try:
        env = load_env()
        creds = AlpacaCreds(
            key=env.alpaca_key,
            secret=env.alpaca_secret,
            base_url=env.alpaca_base_url
        )
        executor = AlpacaExecutor(creds, dry_run=False)
        broker_pos = fetch_broker_positions(executor)
    except Exception as e:
        RF.print_log(f"Failed to initialize Alpaca executor: {e}", "ERROR")
        print("⚠️ Cannot fetch broker positions. Showing local state only.")
        broker_pos = {}
    
    print("=" * 70)
    print("Position Reconciliation")
    print("=" * 70)
    print(f"{'Symbol':<12} {'Local':>15} {'Broker':>15} {'Delta':>15} {'Status'}")
    print("-" * 70)
    
    all_symbols = set(local_pos.keys()) | set(broker_pos.keys())
    
    if not all_symbols:
        print("No positions found (local or broker)")
        return 0
    
    discrepancies = {}
    
    for sym in sorted(all_symbols):
        local = local_pos.get(sym, 0.0)
        broker = broker_pos.get(sym, 0.0)
        delta = local - broker
        
        # Check if discrepancy is significant (> 0.01 shares or > $1 notional)
        is_discrepancy = abs(delta) > 0.01
        
        status = "✅" if not is_discrepancy else "⚠️"
        
        print(f"{sym:<12} {local:>15.3f} {broker:>15.3f} {delta:>15.3f} {status}")
        
        if is_discrepancy:
            discrepancies[sym] = {
                "local": local,
                "broker": broker,
                "delta": delta
            }
    
    print("-" * 70)
    
    if discrepancies:
        print(f"\n⚠️ Position discrepancies detected ({len(discrepancies)} symbols):")
        for sym, details in discrepancies.items():
            print(f"   {sym}: Local={details['local']:.3f}, Broker={details['broker']:.3f}, Delta={details['delta']:.3f}")
        RF.print_log(f"Position discrepancies: {discrepancies}", "RISK")
        return 1
    else:
        print("\n✅ Positions reconciled - no discrepancies")
        RF.print_log("Positions reconciled", "SUCCESS")
        return 0


def main() -> int:
    """Main entry point."""
    try:
        return reconcile()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        RF.print_log(f"Reconciliation failed: {e}", "ERROR")
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

