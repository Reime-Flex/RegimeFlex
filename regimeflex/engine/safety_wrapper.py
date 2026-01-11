# engine/safety_wrapper.py
"""
Shield Safety Wrapper for RegimeFlex Execution Logic

Provides three layers of protection:
1. Stale Data Check - Abort if data older than 60 seconds
2. Slippage Protection - Convert market orders to limit with 0.05% buffer
3. Duplicate Trade Prevention - State lock file to prevent double-dipping
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

from regimeflex.engine.identity import RegimeFlexIdentity as RF
from regimeflex.engine.config import Config
from regimeflex.config.paths import TRADING_STATE_FILE, PROJECT_ROOT
from regimeflex.utils.atomic_file import atomic_write_json, atomic_read_json


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class SafetyError(Exception):
    """Base exception for safety wrapper errors."""
    pass


class StaleDataError(SafetyError):
    """Raised when market data is too old for safe execution."""
    pass


class OrderLockError(SafetyError):
    """Raised when attempting to place a duplicate order."""
    pass


class SlippageProtectionError(SafetyError):
    """Raised when slippage protection cannot be applied."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SafetyConfig:
    """Configuration for safety wrapper."""
    # Stale data check
    stale_data_enabled: bool = True
    stale_threshold_seconds: int = 60
    stale_alert_channel: str = "telegram"  # telegram | discord | log_only
    
    # Slippage protection
    slippage_enabled: bool = True
    slippage_buffer_pct: float = 0.0005  # 0.05%
    force_limit_orders: bool = True
    
    # Duplicate prevention
    duplicate_prevention_enabled: bool = True
    state_file: str = str(TRADING_STATE_FILE)  # Use absolute path from paths module
    lock_timeout_seconds: int = 300  # 5 minutes
    check_on_startup: bool = True


def load_safety_config(root: str | Path = None) -> SafetyConfig:
    """Load safety configuration from config/safety.yaml."""
    if root is None:
        root_path = PROJECT_ROOT
    else:
        root_path = Path(root)
    config_path = root_path / "config" / "safety.yaml"
    
    cfg = SafetyConfig()
    
    if config_path.exists():
        try:
            raw = Config(root_path)._load_yaml("config/safety.yaml") or {}
            
            # Stale data
            stale = raw.get("stale_data", {}) or {}
            cfg.stale_data_enabled = bool(stale.get("enabled", True))
            cfg.stale_threshold_seconds = int(stale.get("threshold_seconds", 60))
            cfg.stale_alert_channel = str(stale.get("alert_channel", "telegram"))
            
            # Slippage protection
            slip = raw.get("slippage_protection", {}) or {}
            cfg.slippage_enabled = bool(slip.get("enabled", True))
            cfg.slippage_buffer_pct = float(slip.get("buffer_pct", 0.0005))
            cfg.force_limit_orders = bool(slip.get("force_limit_orders", True))
            
            # Duplicate prevention
            dup = raw.get("duplicate_prevention", {}) or {}
            cfg.duplicate_prevention_enabled = bool(dup.get("enabled", True))
            # Use absolute path from paths module as default
            state_file_config = dup.get("state_file")
            if state_file_config:
                # If config specifies relative path, make it absolute relative to project root
                cfg.state_file = str(PROJECT_ROOT / state_file_config) if not Path(state_file_config).is_absolute() else str(state_file_config)
            else:
                cfg.state_file = str(TRADING_STATE_FILE)
            cfg.lock_timeout_seconds = int(dup.get("lock_timeout_seconds", 300))
            cfg.check_on_startup = bool(dup.get("check_on_startup", True))
            
        except Exception as e:
            RF.print_log(f"Error loading safety config, using defaults: {e}", "RISK")
    
    return cfg


def get_safety_config() -> SafetyConfig:
    """Convenience function to get safety config from project root."""
    return load_safety_config(PROJECT_ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# Stale Data Check
# ─────────────────────────────────────────────────────────────────────────────

def check_data_freshness(
    data_timestamp: datetime,
    system_time: Optional[datetime] = None,
    threshold_seconds: int = 60
) -> Tuple[bool, float, str]:
    """
    Compare data timestamp with system time.
    
    This checks if Polygon data timestamp is fresh enough for safe execution.
    If data is older than threshold, it may be stale due to market closure,
    network issues, or API delays.
    
    Args:
        data_timestamp: Timestamp of the market data (must be timezone-aware UTC)
        system_time: System time for comparison (defaults to now)
        threshold_seconds: Maximum allowed age in seconds (default 60s)
        
    Returns:
        Tuple of (is_fresh, age_seconds, message)
    """
    if system_time is None:
        system_time = datetime.now(timezone.utc)
    
    # Ensure timestamps are timezone-aware
    if data_timestamp.tzinfo is None:
        data_timestamp = data_timestamp.replace(tzinfo=timezone.utc)
    if system_time.tzinfo is None:
        system_time = system_time.replace(tzinfo=timezone.utc)
    
    age_seconds = (system_time - data_timestamp).total_seconds()
    
    # Handle negative age (data from future - clock skew or timezone issue)
    if age_seconds < 0:
        RF.print_log(f"⚠️ Clock skew detected: data timestamp is {abs(age_seconds):.1f}s in the future", "WARNING")
        # Allow small negative skew (up to 5 seconds)
        if age_seconds < -5:
            msg = f"⛔ CLOCK SKEW: Data timestamp {abs(age_seconds):.1f}s in future"
            return False, age_seconds, msg
    
    if age_seconds > threshold_seconds:
        msg = f"⛔ STALE DATA: {age_seconds:.1f}s old > {threshold_seconds}s threshold"
        return False, age_seconds, msg
    
    msg = f"✅ Data fresh: {age_seconds:.1f}s old"
    return True, age_seconds, msg


def validate_data_freshness(
    data_timestamp: datetime,
    config: Optional[SafetyConfig] = None,
    raise_on_stale: bool = True
) -> Tuple[bool, str]:
    """
    Validate data freshness and optionally raise exception if stale.
    
    Args:
        data_timestamp: Timestamp of the market data
        config: Safety configuration (loads default if None)
        raise_on_stale: If True, raises StaleDataError when data is stale
        
    Returns:
        Tuple of (is_fresh, message)
        
    Raises:
        StaleDataError: If data is stale and raise_on_stale is True
    """
    config = config or get_safety_config()
    
    if not config.stale_data_enabled:
        return True, "Stale data check disabled"
    
    is_fresh, age_seconds, msg = check_data_freshness(
        data_timestamp=data_timestamp,
        threshold_seconds=config.stale_threshold_seconds
    )
    
    if not is_fresh:
        RF.print_log(msg, "ERROR")
        if raise_on_stale:
            raise StaleDataError(
                f"Market data is {age_seconds:.1f} seconds old, "
                f"exceeds {config.stale_threshold_seconds}s safety threshold. "
                "Trade aborted to prevent execution on stale prices."
            )
    
    return is_fresh, msg


# ─────────────────────────────────────────────────────────────────────────────
# Slippage Protection
# ─────────────────────────────────────────────────────────────────────────────

def calculate_limit_price(
    mid_price: float,
    side: str,
    buffer_pct: float = 0.0005
) -> float:
    """
    Calculate limit price with slippage buffer for execution certainty.
    
    For TQQQ/SQQQ volatility, we set limit prices that ensure execution
    while protecting against being "chewed up" by the spread:
    - BUY: mid_price * (1 + buffer) - willing to pay slightly more
    - SELL: mid_price * (1 - buffer) - willing to receive slightly less
    
    Args:
        mid_price: Current mid-market price
        side: "BUY" or "SELL"
        buffer_pct: Buffer percentage (default 0.05% = 0.0005)
        
    Returns:
        Calculated limit price rounded to 2 decimals
    """
    if mid_price <= 0:
        raise SlippageProtectionError(f"Invalid mid_price: {mid_price}")
    
    side_upper = side.upper()
    if side_upper == "BUY":
        # Willing to pay up to 0.05% above mid to ensure fill
        limit = mid_price * (1 + buffer_pct)
    elif side_upper == "SELL":
        # Willing to receive 0.05% below mid to ensure fill
        limit = mid_price * (1 - buffer_pct)
    else:
        raise SlippageProtectionError(f"Invalid side: {side}")
    
    return round(limit, 2)


def apply_slippage_protection(
    order: Dict[str, Any],
    mid_price: float,
    config: Optional[SafetyConfig] = None
) -> Dict[str, Any]:
    """
    Apply slippage protection to an order.
    
    Converts market orders to limit orders with protective buffer.
    
    Args:
        order: Order dictionary with 'side', 'type', etc.
        mid_price: Current mid-market price
        config: Safety configuration
        
    Returns:
        Modified order with limit price applied
    """
    config = config or get_safety_config()
    
    if not config.slippage_enabled:
        return order
    
    order = order.copy()
    order_type = str(order.get("type", "market")).lower()
    side = str(order.get("side", "")).upper()
    
    # Only apply to market orders when force_limit is enabled
    if order_type == "market" and config.force_limit_orders:
        limit_price = calculate_limit_price(
            mid_price=mid_price,
            side=side,
            buffer_pct=config.slippage_buffer_pct
        )
        order["type"] = "limit"
        order["limit_price"] = limit_price
        RF.print_log(
            f"🛡️ Slippage protection: {side} converted to limit @ ${limit_price:.2f} "
            f"(mid=${mid_price:.2f}, buffer={config.slippage_buffer_pct*100:.3f}%)",
            "INFO"
        )
    
    # For existing limit orders, ensure the buffer is protective
    elif order_type == "limit" and order.get("limit_price"):
        existing_limit = float(order["limit_price"])
        protective_limit = calculate_limit_price(
            mid_price=mid_price,
            side=side,
            buffer_pct=config.slippage_buffer_pct
        )
        
        # For BUY: use higher of existing or protective (more aggressive fill)
        # For SELL: use lower of existing or protective (more aggressive fill)
        if side == "BUY":
            if existing_limit < protective_limit:
                order["limit_price"] = protective_limit
                RF.print_log(
                    f"🛡️ Slippage protection: BUY limit adjusted {existing_limit:.2f} → {protective_limit:.2f}",
                    "INFO"
                )
        else:  # SELL
            if existing_limit > protective_limit:
                order["limit_price"] = protective_limit
                RF.print_log(
                    f"🛡️ Slippage protection: SELL limit adjusted {existing_limit:.2f} → {protective_limit:.2f}",
                    "INFO"
                )
    
    return order


# ─────────────────────────────────────────────────────────────────────────────
# Duplicate Trade Prevention (Trading State Lock)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActiveOrder:
    """Represents an active/pending order in the state file."""
    order_key: str
    symbol: str
    side: str
    qty: float
    created_at: str
    status: str = "pending"
    broker_id: Optional[str] = None
    limit_price: Optional[float] = None


@dataclass
class TradingState:
    """Full trading state structure."""
    version: int = 1
    last_updated: str = ""
    active_orders: List[Dict[str, Any]] = field(default_factory=list)
    completed_orders: List[Dict[str, Any]] = field(default_factory=list)
    failed_orders: List[Dict[str, Any]] = field(default_factory=list)


class TradingStateLock:
    """
    Manages trading_state.json to prevent duplicate orders.
    
    Uses file locking to ensure atomic operations in multi-process scenarios.
    """
    
    def __init__(self, state_file: str | Path = None):
        # Use TRADING_STATE_FILE as default if not provided
        if state_file is None:
            state_file = TRADING_STATE_FILE
        # Convert relative paths to absolute relative to PROJECT_ROOT
        self.state_file = Path(state_file)
        if not self.state_file.is_absolute():
            self.state_file = PROJECT_ROOT / self.state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _load_state(self) -> TradingState:
        """Load current state from file with atomic read and file locking."""
        default_data = {
            "version": 1,
            "last_updated": self._now_iso(),
            "active_orders": [],
            "completed_orders": [],
            "failed_orders": []
        }
        
        # Use atomic_read_json for safe reading with file locking
        data = atomic_read_json(self.state_file, default=default_data)
        
        if data is None:
            return TradingState(last_updated=self._now_iso())
        
        try:
            return TradingState(
                version=data.get("version", 1),
                last_updated=data.get("last_updated", ""),
                active_orders=data.get("active_orders", []),
                completed_orders=data.get("completed_orders", []),
                failed_orders=data.get("failed_orders", [])
            )
        except (KeyError, TypeError) as e:
            RF.print_log(f"Error parsing trading state, starting fresh: {e}", "RISK")
            return TradingState(last_updated=self._now_iso())
    
    def _save_state(self, state: TradingState) -> None:
        """Save state to file with atomic write and file locking."""
        state.last_updated = self._now_iso()
        
        # Use atomic_write_json for safe writing with temp file + rename + file locking
        success = atomic_write_json(self.state_file, asdict(state), indent=2)
        
        if not success:
            RF.print_log(f"Failed to save trading state to {self.state_file}", "ERROR")
            raise RuntimeError(f"Failed to save trading state to {self.state_file}")
    
    def generate_order_key(self, symbol: str, side: str, qty: float) -> str:
        """Generate unique key for an order."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{symbol.upper()}_{side.upper()}_{ts}"
    
    def has_active_order(self, symbol: str, side: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if there's an active order for this symbol/side combination.
        
        Returns:
            Tuple of (has_active, order_details)
        """
        state = self._load_state()
        config = get_safety_config()
        now = datetime.now(timezone.utc)
        
        for order in state.active_orders:
            if order.get("symbol", "").upper() == symbol.upper() and \
               order.get("side", "").upper() == side.upper():
                # Check if order has expired (stale lock)
                created_str = order.get("created_at", "")
                try:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    age_seconds = (now - created).total_seconds()
                    if age_seconds > config.lock_timeout_seconds:
                        # Stale lock, can be overwritten
                        RF.print_log(
                            f"Stale order lock found ({age_seconds:.0f}s > {config.lock_timeout_seconds}s), "
                            f"will overwrite: {order.get('order_key')}",
                            "RISK"
                        )
                        continue
                except (ValueError, TypeError):
                    pass
                
                return True, order
        
        return False, None
    
    def acquire_lock(self, symbol: str, side: str, qty: float, limit_price: Optional[float] = None) -> str:
        """
        Acquire a lock for a new order.
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            qty: Order quantity
            limit_price: Optional limit price
            
        Returns:
            Order key if lock acquired
            
        Raises:
            OrderLockError: If a conflicting active order exists
        """
        has_active, existing = self.has_active_order(symbol, side)
        
        if has_active:
            raise OrderLockError(
                f"Cannot place {side} order for {symbol}: "
                f"Active order already exists (key={existing.get('order_key')}, "
                f"created={existing.get('created_at')}). "
                "This prevents double-dipping due to loop errors."
            )
        
        # Create new order entry
        order_key = self.generate_order_key(symbol, side, qty)
        new_order = ActiveOrder(
            order_key=order_key,
            symbol=symbol.upper(),
            side=side.upper(),
            qty=qty,
            created_at=self._now_iso(),
            status="pending",
            limit_price=limit_price
        )
        
        state = self._load_state()
        state.active_orders.append(asdict(new_order))
        self._save_state(state)
        
        RF.print_log(f"🔒 Order lock acquired: {order_key}", "INFO")
        return order_key
    
    def release_lock(self, order_key: str, final_status: str = "completed", 
                     broker_id: Optional[str] = None) -> None:
        """
        Release an order lock after completion or failure.
        
        Args:
            order_key: The order key to release
            final_status: "completed" or "failed"
            broker_id: Optional broker order ID
        """
        state = self._load_state()
        
        # Find and remove from active orders
        remaining_active = []
        released_order = None
        
        for order in state.active_orders:
            if order.get("order_key") == order_key:
                released_order = order
                released_order["broker_id"] = broker_id
                released_order["completed_at"] = self._now_iso()
            else:
                remaining_active.append(order)
        
        state.active_orders = remaining_active
        
        # Move to appropriate completed/failed list
        if released_order:
            if final_status == "completed":
                state.completed_orders.append(released_order)
            else:
                state.failed_orders.append(released_order)
            
            # Keep only last 100 completed/failed orders
            state.completed_orders = state.completed_orders[-100:]
            state.failed_orders = state.failed_orders[-100:]
        
        self._save_state(state)
        RF.print_log(f"🔓 Order lock released: {order_key} ({final_status})", "INFO")
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of all active orders."""
        state = self._load_state()
        return state.active_orders.copy()
    
    def cleanup_stale_locks(self) -> int:
        """
        Remove stale locks that have exceeded timeout.
        
        Returns:
            Number of stale locks removed
        """
        config = get_safety_config()
        state = self._load_state()
        now = datetime.now(timezone.utc)
        
        remaining = []
        stale_count = 0
        
        for order in state.active_orders:
            created_str = order.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_seconds = (now - created).total_seconds()
                
                if age_seconds > config.lock_timeout_seconds:
                    stale_count += 1
                    order["completed_at"] = self._now_iso()
                    order["status"] = "stale_expired"
                    state.failed_orders.append(order)
                    RF.print_log(f"🧹 Cleaned up stale lock: {order.get('order_key')}", "RISK")
                else:
                    remaining.append(order)
            except (ValueError, TypeError):
                remaining.append(order)
        
        state.active_orders = remaining
        state.failed_orders = state.failed_orders[-100:]
        self._save_state(state)
        
        return stale_count
    
    @contextmanager
    def order_context(self, symbol: str, side: str, qty: float, 
                      limit_price: Optional[float] = None):
        """
        Context manager for order execution with automatic lock management.
        
        Usage:
            with lock.order_context("TQQQ", "BUY", 100) as order_key:
                # Execute order
                result = place_order(...)
        """
        order_key = self.acquire_lock(symbol, side, qty, limit_price)
        try:
            yield order_key
            self.release_lock(order_key, "completed")
        except Exception as e:
            self.release_lock(order_key, "failed")
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Main Safety Wrapper Class
# ─────────────────────────────────────────────────────────────────────────────

class SafetyWrapper:
    """
    Main safety wrapper that orchestrates all safety checks.
    
    Usage:
        safety = SafetyWrapper()
        
        # Check data freshness
        safety.validate_freshness(data_timestamp)
        
        # Apply slippage protection
        protected_order = safety.protect_order(order, mid_price)
        
        # Execute with duplicate prevention
        with safety.order_lock(symbol, side, qty):
            result = executor.place_order(protected_order)
    """
    
    def __init__(self, config: Optional[SafetyConfig] = None):
        self.config = config or get_safety_config()
        self.state_lock = TradingStateLock(self.config.state_file)
        
        # Cleanup stale locks on startup if configured
        if self.config.check_on_startup and self.config.duplicate_prevention_enabled:
            stale_count = self.state_lock.cleanup_stale_locks()
            if stale_count > 0:
                RF.print_log(f"🧹 Cleaned up {stale_count} stale order locks on startup", "INFO")
    
    def validate_freshness(self, data_timestamp: datetime, raise_on_stale: bool = True) -> Tuple[bool, float, str]:
        """
        Validate data freshness and return detailed result.
        
        Returns:
            Tuple of (is_fresh, age_seconds, message)
        """
        if not self.config.stale_data_enabled:
            return True, 0.0, "Stale data check disabled"
        
        is_fresh, age_seconds, msg = check_data_freshness(
            data_timestamp=data_timestamp,
            threshold_seconds=self.config.stale_threshold_seconds
        )
        
        if not is_fresh and raise_on_stale:
            raise StaleDataError(
                f"Market data is {age_seconds:.1f} seconds old, "
                f"exceeds {self.config.stale_threshold_seconds}s safety threshold. "
                "Trade aborted to prevent execution on stale prices."
            )
        
        return is_fresh, age_seconds, msg
    
    def protect_order(self, order: Dict[str, Any], mid_price: float) -> Dict[str, Any]:
        """Apply slippage protection to order. See apply_slippage_protection()."""
        return apply_slippage_protection(order, mid_price, self.config)
    
    def check_duplicates(self, symbol: str, side: str) -> Tuple[bool, Optional[Dict]]:
        """Check for existing active orders."""
        if not self.config.duplicate_prevention_enabled:
            return False, None
        return self.state_lock.has_active_order(symbol, side)
    
    def order_lock(self, symbol: str, side: str, qty: float, 
                   limit_price: Optional[float] = None):
        """Get order context manager for duplicate prevention."""
        if not self.config.duplicate_prevention_enabled:
            @contextmanager
            def noop():
                yield None
            return noop()
        return self.state_lock.order_context(symbol, side, qty, limit_price)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current safety wrapper status."""
        active_orders = self.state_lock.get_active_orders() if self.config.duplicate_prevention_enabled else []
        
        return {
            "config": asdict(self.config),
            "active_orders": active_orders,
            "active_order_count": len(active_orders),
            "status": "operational"
        }
    
    def send_alert(self, message: str, level: str = "ERROR") -> None:
        """
        Send alert through configured channel.
        
        This integrates with the existing telemetry/notification system.
        """
        RF.print_log(f"🚨 SAFETY ALERT: {message}", level)
        
        # Integration with existing telemetry would go here
        # For now, we log and let the existing notification system pick it up
        # The Guardian module handles Telegram/Discord alerts


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

def wrap_order_execution(
    order_func,
    symbol: str,
    side: str,
    qty: float,
    mid_price: float,
    data_timestamp: datetime,
    order_kwargs: Dict[str, Any]
) -> Any:
    """
    Convenience function to wrap any order execution with full safety checks.
    
    Args:
        order_func: The function to call to execute the order
        symbol: Trading symbol
        side: BUY or SELL
        qty: Order quantity
        mid_price: Current mid-market price
        data_timestamp: Timestamp of the price data
        order_kwargs: Additional arguments for order_func
        
    Returns:
        Result from order_func
        
    Raises:
        StaleDataError: If data is too old
        OrderLockError: If duplicate order exists
    """
    safety = SafetyWrapper()
    
    # 1. Check data freshness
    safety.validate_freshness(data_timestamp)
    
    # 2. Check for duplicates
    has_dup, dup_order = safety.check_duplicates(symbol, side)
    if has_dup:
        raise OrderLockError(
            f"Duplicate order blocked: {symbol} {side} already pending "
            f"(key={dup_order.get('order_key')})"
        )
    
    # 3. Apply slippage protection to order kwargs
    protected_kwargs = order_kwargs.copy()
    if "limit_price" not in protected_kwargs or protected_kwargs.get("type") == "market":
        protected_kwargs["limit_price"] = calculate_limit_price(
            mid_price, side, safety.config.slippage_buffer_pct
        )
        protected_kwargs["type"] = "limit"
    
    # 4. Execute with lock
    with safety.order_lock(symbol, side, qty, protected_kwargs.get("limit_price")):
        result = order_func(**protected_kwargs)
    
    return result
