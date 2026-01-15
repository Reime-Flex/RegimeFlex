# engine/drift.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional


@dataclass
class DriftAlert:
    """Represents a position drift alert with severity level."""
    symbol: str
    local_qty: float
    broker_qty: float
    drift_shares: float
    drift_notional: float
    severity: str  # "INFO" | "WARNING" | "CRITICAL"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DriftConfig:
    """Configuration for drift detection thresholds."""
    # Share-based thresholds
    info_shares: float = 0.5
    warn_shares: float = 5.0
    crit_shares: float = 50.0
    # Notional-based thresholds (in dollars)
    info_notional: float = 50.0
    warn_notional: float = 500.0
    crit_notional: float = 5000.0
    # Actions
    block_on_critical: bool = False

    @classmethod
    def from_dict(cls, d: Optional[Dict]) -> "DriftConfig":
        if not d:
            return cls()
        return cls(
            info_shares=float(d.get("info_shares", 0.5)),
            warn_shares=float(d.get("warn_shares", 5.0)),
            crit_shares=float(d.get("crit_shares", 50.0)),
            info_notional=float(d.get("info_notional", 50.0)),
            warn_notional=float(d.get("warn_notional", 500.0)),
            crit_notional=float(d.get("crit_notional", 5000.0)),
            block_on_critical=bool(d.get("block_on_critical", False)),
        )


def compute_position_drift_with_alerts(
    local_pos: Dict[str, float],
    broker_pos: Dict[str, float],
    prices: Dict[str, float],
    config: Optional[DriftConfig] = None,
) -> Tuple[bool, List[DriftAlert]]:
    """
    Enhanced drift detection with tiered alerting.

    Args:
        local_pos: Local positions {SYMBOL: qty}
        broker_pos: Broker positions {SYMBOL: qty}
        prices: Current prices {SYMBOL: price}
        config: Drift configuration thresholds

    Returns:
        (has_critical, alerts) - Whether critical drift found, and list of all alerts
    """
    if config is None:
        config = DriftConfig()

    alerts: List[DriftAlert] = []
    has_critical = False

    all_symbols = set(local_pos.keys()) | set(broker_pos.keys())

    for sym in all_symbols:
        local = local_pos.get(sym, 0.0)
        broker = broker_pos.get(sym, 0.0)
        price = prices.get(sym, 0.0)

        drift_shares = broker - local
        drift_notional = abs(drift_shares) * price

        # Skip if below minimum threshold
        if abs(drift_shares) < 1e-6 and drift_notional < config.info_notional:
            continue

        # Determine severity based on thresholds
        severity = None

        if drift_notional >= config.crit_notional or abs(drift_shares) >= config.crit_shares:
            severity = "CRITICAL"
            has_critical = True
        elif drift_notional >= config.warn_notional or abs(drift_shares) >= config.warn_shares:
            severity = "WARNING"
        elif drift_notional >= config.info_notional or abs(drift_shares) >= config.info_shares:
            severity = "INFO"

        if severity:
            alerts.append(DriftAlert(
                symbol=sym,
                local_qty=round(local, 6),
                broker_qty=round(broker, 6),
                drift_shares=round(drift_shares, 6),
                drift_notional=round(drift_notional, 2),
                severity=severity,
            ))

    # Sort by severity (CRITICAL first, then WARNING, then INFO)
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    return has_critical, alerts


def compute_position_drift(
    local_pos: Dict[str, float],     # reconciled: positions_before (effective), UPPERCASE
    broker_pos: Dict[str, float] | None,  # snapshot from broker (if available), UPPERCASE
    prices: Dict[str, float],        # UPPERCASE, latest common-date prices
    symbols: List[str],              # which symbols to check (e.g., ["QQQ","PSQ"])
    shares_eps: float = 1.0,
    notional_eps: float = 200.0,
) -> Tuple[bool, Dict[str, dict], str]:
    """
    Returns (warn, per_sym, note)
      - warn: True if any symbol exceeds thresholds
      - per_sym: {SYM: {"local_sh":..,"broker_sh":..,"d_sh":..,"d_notional":..}}
      - note: "no_broker_snapshot" | "OK" | "WARN"
    """
    if not broker_pos:
        return False, {}, "no_broker_snapshot"

    warn = False
    out: Dict[str, dict] = {}
    for s in symbols:
        ls = float(local_pos.get(s, 0.0))
        bs = float(broker_pos.get(s, 0.0))
        d_sh = bs - ls
        px  = float(prices.get(s, 0.0))
        d_not = abs(d_sh) * (px if px == px else 0.0)
        hit = (abs(d_sh) > shares_eps) or (d_not > notional_eps)
        warn = warn or hit
        out[s] = {
            "local_sh": round(ls, 6),
            "broker_sh": round(bs, 6),
            "d_sh": round(d_sh, 6),
            "d_notional": round(d_not, 2),
            "hit": hit,
        }
    return warn, out, ("WARN" if warn else "OK")

