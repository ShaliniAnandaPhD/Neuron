#!/usr/bin/env python3
"""
Circuit Breaker - System Protection and Fault Tolerance
Advanced circuit breaker implementation for high-velocity pipeline protection

This module provides:
- Circuit breaker pattern implementation
- Automatic failure detection and recovery
- Health monitoring and statistics
- Configurable thresholds and timeouts
- System-wide protection coordination
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading

from .config_manager import PipelineConfig


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker state change event"""
    timestamp: datetime
    previous_state: CircuitState
    new_state: CircuitState
    trigger: str
    failure_count: int
    success_count: int


class CircuitBreaker:
    """
    Individual circuit breaker for protecting specific operations
    
    Implements the circuit breaker pattern to prevent cascading failures
    and provide fast failure responses when services are unhealthy.
    """
    
    def __init__(self, name: str, failure_threshold: int = 5, 
                 timeout_seconds: float = 30.0, success_threshold: int = 3):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change = datetime.now()
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.trip_count = 0
        
        # Event tracking
        self.state_history: List[CircuitBreakerEvent] = []
        self.max_history = 100
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Event callbacks
        self.state_change_callbacks: List[Callable[[CircuitBreakerEvent], None]] = []
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.logger.info(f"Circuit breaker '{name}' initialized")
    
    def add_state_change_callback(self, callback: Callable[[CircuitBreakerEvent], None]):
        """Add callback for state change events"""
        self.state_change_callbacks.append(callback)
    
    def can_proceed(self) -> bool:
        """Check if requests can proceed through the circuit"""
        with self.lock:
            self.total_requests += 1
            
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if self.last_failure_time:
                    time_since_failure = datetime.now() - self.last_failure_time
                    if time_since_failure.total_seconds() >= self.timeout_seconds:
                        self._transition_to_half_open()
                        return True
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                return True
            
            return False
    
    def record_success(self):
        """Record a successful operation"""
        with self.lock:
            self.total_successes += 1
            
            if self.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
                
            elif self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                
                # Close circuit after enough successes
                if self.success_count >= self.success_threshold:
                    self._transition_to_closed()
    
    def record_failure(self):
        """Record a failed operation"""
        with self.lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.CLOSED:
                # Open circuit if failure threshold is reached
                if self.failure_count >= self.failure_threshold:
                    self._transition_to_open()
                    
            elif self.state == CircuitState.HALF_OPEN:
                # Immediately open on any failure in half-open state
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit to open state"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.trip_count += 1
        self.success_count = 0
        
        event = CircuitBreakerEvent(
            timestamp=datetime.now(),
            previous_state=old_state,
            new_state=CircuitState.OPEN,
            trigger=f"failure_threshold_reached({self.failure_count})",
            failure_count=self.failure_count,
            success_count=self.success_count
        )
        
        self._record_state_change(event)
        self.logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")
    
    def _transition_to_half_open(self):
        """Transition circuit to half-open state"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        
        event = CircuitBreakerEvent(
            timestamp=datetime.now(),
            previous_state=old_state,
            new_state=CircuitState.HALF_OPEN,
            trigger=f"timeout_elapsed({self.timeout_seconds}s)",
            failure_count=self.failure_count,
            success_count=self.success_count
        )
        
        self._record_state_change(event)
        self.logger.info(f"Circuit breaker '{self.name}' transitioned to half-open")
    
    def _transition_to_closed(self):
        """Transition circuit to closed state"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        
        event = CircuitBreakerEvent(
            timestamp=datetime.now(),
            previous_state=old_state,
            new_state=CircuitState.CLOSED,
            trigger=f"success_threshold_reached({self.success_count})",
            failure_count=self.failure_count,
            success_count=self.success_count
        )
        
        self._record_state_change(event)
        self.logger.info(f"Circuit breaker '{self.name}' closed after recovery")
    
    def _record_state_change(self, event: CircuitBreakerEvent):
        """Record state change event"""
        self.state_history.append(event)
        self.last_state_change = event.timestamp
        
        # Maintain history size
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history//2:]
        
        # Notify callbacks
        for callback in self.state_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"State change callback failed: {e}")
    
    def force_open(self):
        """Manually open the circuit breaker"""
        with self.lock:
            if self.state != CircuitState.OPEN:
                self._transition_to_open()
    
    def force_close(self):
        """Manually close the circuit breaker"""
        with self.lock:
            if self.state != CircuitState.CLOSED:
                old_state = self.state
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                
                event = CircuitBreakerEvent(
                    timestamp=datetime.now(),
                    previous_state=old_state,
                    new_state=CircuitState.CLOSED,
                    trigger="manual_reset",
                    failure_count=self.failure_count,
                    success_count=self.success_count
                )
                
                self._record_state_change(event)
                self.logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker statistics"""
        with self.lock:
            failure_rate = (self.total_failures / self.total_requests) if self.total_requests > 0 else 0
            
            return {
                "name": self.name,
                "state": self.state.value,
                "configuration": {
                    "failure_threshold": self.failure_threshold,
                    "timeout_seconds": self.timeout_seconds,
                    "success_threshold": self.success_threshold
                },
                "current_counts": {
                    "failure_count": self.failure_count,
                    "success_count": self.success_count
                },
                "totals": {
                    "total_requests": self.total_requests,
                    "total_failures": self.total_failures,
                    "total_successes": self.total_successes,
                    "trip_count": self.trip_count
                },
                "metrics": {
                    "failure_rate": failure_rate,
                    "uptime_percentage": (1 - failure_rate) * 100,
                    "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
                    "last_state_change": self.last_state_change.isoformat()
                },
                "recent_events": [
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "previous_state": event.previous_state.value,
                        "new_state": event.new_state.value,
                        "trigger": event.trigger
                    }
                    for event in self.state_history[-5:]  # Last 5 events
                ]
            }
    
    def reset_statistics(self):
        """Reset all statistics while preserving current state"""
        with self.lock:
            self.total_requests = 0
            self.total_failures = 0
            self.total_successes = 0
            # Don't reset trip_count - it's cumulative
            # Don't reset current failure/success counts - they affect state
            
            self.logger.info(f"Statistics reset for circuit breaker '{self.name}'")


class SystemCircuitBreaker:
    """
    System-wide circuit breaker coordination
    
    Manages multiple circuit breakers and provides system-level
    protection and monitoring capabilities.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize circuit breakers
        self.breakers: Dict[str, CircuitBreaker] = {}
        
        # Create default system circuit breaker
        self.system_breaker = CircuitBreaker(
            name="system",
            failure_threshold=config.circuit_breaker_failure_threshold,
            timeout_seconds=config.circuit_breaker_timeout_seconds,
            success_threshold=config.circuit_breaker_success_threshold
        )
        
        self.breakers["system"] = self.system_breaker