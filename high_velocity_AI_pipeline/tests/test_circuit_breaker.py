#!/usr/bin/env python3
"""
Unit Tests for Circuit Breaker (src/circuit_breaker.py)

This test suite verifies the state transitions and logic of the CircuitBreaker class,
ensuring it correctly protects the system from cascading failures.
"""

import pytest
import time

# Add src to path to allow direct import of modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.circuit_breaker import CircuitBreaker, CircuitState

@pytest.fixture
def circuit_breaker() -> CircuitBreaker:
    """
    Provides a CircuitBreaker instance with a short timeout for efficient testing.
    It is configured to open after 2 failures and close after 2 successes.
    """
    return CircuitBreaker(
        name="test_breaker",
        failure_threshold=2,
        timeout_seconds=0.1,
        success_threshold=2
    )

def test_initial_state_is_closed(circuit_breaker: CircuitBreaker):
    """Verifies that the circuit breaker starts in the CLOSED state and allows requests."""
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.can_proceed() is True

def test_opens_after_reaching_failure_threshold(circuit_breaker: CircuitBreaker):
    """
    Tests that the circuit breaker transitions from CLOSED to OPEN
    after the number of failures reaches the configured threshold.
    """
    # Arrange: Record one failure, should remain closed
    circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 1

    # Act: Record a second failure, which should trip the breaker
    circuit_breaker.record_failure()

    # Assert: Breaker is now OPEN and should not allow requests
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.trip_count == 1
    assert circuit_breaker.can_proceed() is False

def test_transitions_to_half_open_after_timeout(circuit_breaker: CircuitBreaker):
    """
    Tests that the circuit breaker transitions from OPEN to HALF_OPEN
    after the timeout period has elapsed, allowing a test request.
    """
    # Arrange: Trip the breaker to the OPEN state
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()
    assert circuit_breaker.state == CircuitState.OPEN

    # Act: Wait for the timeout to expire
    time.sleep(0.15)

    # Assert: The next check should find the timeout has passed, transition
    # the state to HALF_OPEN, and allow one request to proceed.
    assert circuit_breaker.can_proceed() is True
    assert circuit_breaker.state == CircuitState.HALF_OPEN

def test_closes_after_success_threshold_in_half_open(circuit_breaker: CircuitBreaker):
    """
    Tests that the circuit breaker transitions from HALF_OPEN back to CLOSED
    after enough successful operations are recorded.
    """
    # Arrange: Move the breaker to HALF_OPEN state
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()
    time.sleep(0.15)
    circuit_breaker.can_proceed() # This call moves it to HALF_OPEN
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # Act: Record successful operations
    circuit_breaker.record_success()
    assert circuit_breaker.state == CircuitState.HALF_OPEN # Still half-open after one success
    circuit_breaker.record_success() # Second success should close it

    # Assert: Breaker is now CLOSED and has reset its internal counters
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.success_count == 0 # Success count resets upon closing

def test_reopens_on_failure_in_half_open_state(circuit_breaker: CircuitBreaker):
    """
    Tests that a single failure in the HALF_OPEN state immediately
    transitions the circuit breaker back to the OPEN state.
    """
    # Arrange: Move the breaker to HALF_OPEN state
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()
    time.sleep(0.15)
    circuit_breaker.can_proceed() # Move to HALF_OPEN
    assert circuit_breaker.state == CircuitState.HALF_OPEN

    # Act: Record a single failure
    circuit_breaker.record_failure()

    # Assert: Breaker should immediately re-open
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.can_proceed() is False
