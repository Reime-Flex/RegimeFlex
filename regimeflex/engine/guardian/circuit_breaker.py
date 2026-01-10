"""
Guardian Circuit Breaker Module
================================
Implements the circuit breaker pattern for API calls to prevent cascade failures.

Features:
- Failure counting per service
- Exponential backoff retry
- Auto-recovery after timeout
- Emergency alert escalation
"""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, TypeVar

from ..identity import RegimeFlexIdentity as RF
from ..config import Config

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, calls pass through
    OPEN = "open"          # Circuit is broken, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, service: str, failures: int, message: str = ""):
        self.service = service
        self.failures = failures
        super().__init__(message or f"Circuit breaker open for {service} after {failures} failures")


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker."""
    max_failures: int = 3
    retry_delays: List[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])
    reset_timeout_sec: float = 300.0
    emergency_on_open: bool = True


@dataclass
class CircuitBreakerState:
    """Runtime state for a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_trace: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascade failures.
    
    Usage:
        breaker = CircuitBreaker("alpaca")
        
        try:
            result = breaker.execute(requests.post, url, json=data)
        except CircuitBreakerError:
            # Handle circuit open
            pass
    """
    
    # Class-level registry of all breakers
    _registry: Dict[str, "CircuitBreaker"] = {}
    _registry_lock = Lock()
    
    def __init__(
        self,
        service_name: str,
        max_failures: int = 3,
        retry_delays: Optional[List[float]] = None,
        reset_timeout_sec: float = 300.0,
        emergency_on_open: bool = True,
        root: Path | str = "."
    ):
        self.service_name = service_name
        self.config = CircuitBreakerConfig(
            max_failures=max_failures,
            retry_delays=retry_delays or [1.0, 2.0, 4.0],
            reset_timeout_sec=reset_timeout_sec,
            emergency_on_open=emergency_on_open
        )
        self._state = CircuitBreakerState()
        self._lock = Lock()
        self._root = Path(root) if isinstance(root, str) else root
        self._alert_manager = None  # Lazy load to avoid circular import
        
        # Load service-specific config if available
        self._load_config()
        
        # Register this breaker
        with self._registry_lock:
            self._registry[service_name] = self
    
    def _load_config(self) -> None:
        """Load service-specific configuration from guardian.yaml."""
        try:
            cfg = Config(self._root)
            guardian = cfg._load_yaml("config/guardian.yaml") or {}
            cb_cfg = guardian.get("circuit_breaker", {})
            
            # Global defaults
            self.config.max_failures = cb_cfg.get("max_failures", self.config.max_failures)
            self.config.retry_delays = cb_cfg.get("retry_delays", self.config.retry_delays)
            self.config.reset_timeout_sec = cb_cfg.get("reset_timeout_sec", self.config.reset_timeout_sec)
            self.config.emergency_on_open = cb_cfg.get("emergency_on_open", self.config.emergency_on_open)
            
            # Service-specific overrides
            services = cb_cfg.get("services", {})
            if self.service_name in services:
                svc_cfg = services[self.service_name]
                self.config.max_failures = svc_cfg.get("max_failures", self.config.max_failures)
                
        except Exception as e:
            RF.print_log(f"Failed to load circuit breaker config: {e}", "WARNING")
    
    def _get_alert_manager(self):
        """Lazy load alert manager to avoid circular imports."""
        if self._alert_manager is None:
            from .alerting import get_alert_manager
            self._alert_manager = get_alert_manager(self._root)
        return self._alert_manager
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._state.opened_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._state.opened_at).total_seconds()
        return elapsed >= self.config.reset_timeout_sec
    
    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._state.failure_count = 0
            self._state.last_success_time = datetime.now(timezone.utc)
            self._state.last_error = None
            self._state.last_error_trace = None
            
            if self._state.state != CircuitState.CLOSED:
                RF.print_log(f"Circuit breaker [{self.service_name}] CLOSED (recovered)", "SUCCESS")
                self._state.state = CircuitState.CLOSED
                self._state.opened_at = None
    
    def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = datetime.now(timezone.utc)
            self._state.last_error = str(error)
            self._state.last_error_trace = traceback.format_exc()
            
            RF.print_log(
                f"Circuit breaker [{self.service_name}] failure {self._state.failure_count}/{self.config.max_failures}: {error}",
                "ERROR"
            )
            
            if self._state.failure_count >= self.config.max_failures:
                self._open_circuit()
    
    def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        self._state.state = CircuitState.OPEN
        self._state.opened_at = datetime.now(timezone.utc)
        
        RF.print_log(
            f"Circuit breaker [{self.service_name}] OPEN after {self._state.failure_count} failures",
            "ERROR"
        )
        
        # Send emergency alert
        if self.config.emergency_on_open:
            try:
                alert_mgr = self._get_alert_manager()
                alert_mgr.send_emergency(
                    error_type="CIRCUIT_BREAKER_OPEN",
                    error_message=f"Service {self.service_name} has failed {self._state.failure_count} times",
                    trace=self._state.last_error_trace,
                    service=self.service_name
                )
            except Exception as e:
                RF.print_log(f"Failed to send emergency alert: {e}", "ERROR")
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: The function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            The result of func
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If func raises and max retries exceeded
        """
        # Check circuit state
        with self._lock:
            if self._state.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    RF.print_log(f"Circuit breaker [{self.service_name}] attempting reset (HALF_OPEN)", "INFO")
                    self._state.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerError(self.service_name, self._state.failure_count)
        
        # Attempt execution with retries
        last_error: Optional[Exception] = None
        retry_delays = self.config.retry_delays.copy()
        
        for attempt in range(len(retry_delays) + 1):
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
                
            except Exception as e:
                last_error = e
                self._record_failure(e)
                
                # Check if circuit just opened
                if self._state.state == CircuitState.OPEN:
                    raise CircuitBreakerError(
                        self.service_name,
                        self._state.failure_count,
                        f"Circuit opened: {e}"
                    )
                
                # Sleep before retry if we have retries left
                if retry_delays:
                    delay = retry_delays.pop(0)
                    RF.print_log(f"Retrying {self.service_name} in {delay}s...", "WARNING")
                    time.sleep(delay)
        
        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state in circuit breaker")
    
    def is_open(self) -> bool:
        """Check if circuit is open (blocking calls)."""
        return self._state.state == CircuitState.OPEN
    
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitBreakerState()
            RF.print_log(f"Circuit breaker [{self.service_name}] manually reset", "INFO")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state as a dictionary."""
        return {
            "service": self.service_name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "max_failures": self.config.max_failures,
            "last_failure": self._state.last_failure_time.isoformat() if self._state.last_failure_time else None,
            "last_success": self._state.last_success_time.isoformat() if self._state.last_success_time else None,
            "opened_at": self._state.opened_at.isoformat() if self._state.opened_at else None,
            "last_error": self._state.last_error
        }
    
    @classmethod
    def get_all_states(cls) -> Dict[str, Dict[str, Any]]:
        """Get state of all registered circuit breakers."""
        with cls._registry_lock:
            return {name: breaker.get_state() for name, breaker in cls._registry.items()}
    
    @classmethod
    def get_breaker(cls, service_name: str) -> Optional["CircuitBreaker"]:
        """Get a circuit breaker by service name."""
        with cls._registry_lock:
            return cls._registry.get(service_name)
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        with cls._registry_lock:
            for breaker in cls._registry.values():
                breaker.reset()


# Pre-configured breakers for common services
def get_alpaca_breaker(root: Path | str = ".") -> CircuitBreaker:
    """Get or create the Alpaca API circuit breaker."""
    existing = CircuitBreaker.get_breaker("alpaca")
    if existing:
        return existing
    return CircuitBreaker("alpaca", root=root)


def get_polygon_breaker(root: Path | str = ".") -> CircuitBreaker:
    """Get or create the Polygon API circuit breaker."""
    existing = CircuitBreaker.get_breaker("polygon")
    if existing:
        return existing
    return CircuitBreaker("polygon", max_failures=5, root=root)
