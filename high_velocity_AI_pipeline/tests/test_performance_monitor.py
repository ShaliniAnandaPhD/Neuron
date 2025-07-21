#!/usr/bin/env python3
"""
Unit Tests for Performance Monitor (src/performance_monitor.py)

This test suite verifies the accuracy of the metrics collection and calculation
within the PerformanceMonitor and its helper classes like LatencyTracker and
ThroughputTracker.
"""

import pytest
import time
from datetime import datetime

# Add src to path to allow direct import of modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.performance_monitor import PerformanceMonitor, LatencyTracker, ThroughputTracker, AgentType
from src.config_manager import PipelineConfig

@pytest.fixture
def mock_config() -> PipelineConfig:
    """Provides a mock PipelineConfig object."""
    config = MagicMock(spec=PipelineConfig)
    config.enable_csv_export = False # Disable exports for tests
    return config

@pytest.fixture
def latency_tracker() -> LatencyTracker:
    """Provides a clean instance of LatencyTracker for each test."""
    return LatencyTracker()

def test_latency_percentile_calculation(latency_tracker: LatencyTracker):
    """
    Tests the accuracy of P50, P95, and P99 percentile calculations.
    """
    # Arrange: Record a list of 100 latency measurements from 1 to 100
    latencies = list(range(1, 101))
    for lat in latencies:
        latency_tracker.record_latency(lat, AgentType.STANDARD)

    # Act
    percentiles = latency_tracker.get_percentiles()

    # Assert: Check the calculated percentiles
    # For a sorted list of 100 items, the Nth percentile is the Nth item.
    assert percentiles['p50'] == 50
    assert percentiles['p95'] == 95
    assert percentiles['p99'] == 99
    assert percentiles['mean'] == 50.5

def test_agent_performance_comparison(latency_tracker: LatencyTracker):
    """
    Tests that the monitor can correctly calculate and compare performance
    metrics for different agents.
    """
    # Arrange: Record latencies for both standard and ultra-fast agents
    latency_tracker.record_latency(100, AgentType.STANDARD, success=True)
    latency_tracker.record_latency(120, AgentType.STANDARD, success=True)
    latency_tracker.record_latency(20, AgentType.ULTRA_FAST, success=True)
    latency_tracker.record_latency(30, AgentType.ULTRA_FAST, success=True)
    latency_tracker.record_latency(500, AgentType.STANDARD, success=False) # Failed request

    # Act
    comparison = latency_tracker.get_agent_performance_comparison()

    # Assert: Check the calculated stats for each agent
    assert comparison[AgentType.STANDARD]['mean_latency'] == 110.0
    assert comparison[AgentType.STANDARD]['count'] == 2 # Only successful requests are counted for latency mean
    assert comparison[AgentType.STANDARD]['success_rate'] == pytest.approx(2/3)

    assert comparison[AgentType.ULTRA_FAST]['mean_latency'] == 25.0
    assert comparison[AgentType.ULTRA_FAST]['count'] == 2
    assert comparison[AgentType.ULTRA_FAST]['success_rate'] == 1.0

def test_throughput_tracking():
    """
    Tests the ThroughputTracker's ability to calculate messages per second
    over a sliding time window.
    """
    # Arrange: Use a short window for easier testing
    tracker = ThroughputTracker(window_size_seconds=1.0)

    # Act 1: Record 50 messages over ~0.5 seconds
    for _ in range(50):
        tracker.record_message()
        time.sleep(0.01)
    
    # Assert 1: Throughput should be approximately 50 msg/sec
    # (It will be slightly less than 100 because the window is 1s but we only filled 0.5s)
    assert 90 < tracker.get_current_throughput() < 110

    # Act 2: Wait for the time window to slide past the recorded messages
    time.sleep(1.1)

    # Assert 2: Throughput should now be 0 as the messages are outside the window
    assert tracker.get_current_throughput() == 0.0

    # Act 3: Record a new batch of messages
    tracker.record_message(count=200)

    # Assert 3: Throughput should be high again
    assert tracker.get_current_throughput() > 190.0
