#!/usr/bin/env python3
"""
Unit Tests for High-Velocity AI Pipeline Core (src/pipeline_core.py)

This test suite verifies the core orchestration logic of the pipeline,
focusing on the AdaptiveHotSwapController and the interaction between
the main pipeline components.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Add src to path to allow direct import of modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline_core import AdaptiveHotSwapController, SwapTrigger, AgentType, HighVelocityPipeline
from src.config_manager import PipelineConfig
from src.performance_monitor import PerformanceMonitor

# Pytest marker for asyncio tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_config() -> PipelineConfig:
    """Provides a mock PipelineConfig object with typical settings."""
    config = MagicMock(spec=PipelineConfig)
    config.latency_threshold_ms = 100.0
    config.safe_latency_threshold_ms = 70.0
    config.safe_throughput_threshold = 600.0
    config.max_agent_swaps = 10
    config.cooldown_period_seconds = 5.0 # Using a float
    config.default_agent = "standard"
    return config

@pytest.fixture
def mock_performance_monitor() -> PerformanceMonitor:
    """Provides a mock PerformanceMonitor object."""
    # Use AsyncMock for methods that are awaited
    monitor = MagicMock(spec=PerformanceMonitor)
    monitor.get_recent_p99_latency = MagicMock()
    monitor.get_current_throughput = MagicMock()
    monitor.get_recent_error_rate = MagicMock()
    monitor.record_agent_swap = MagicMock()
    return monitor

@pytest.fixture
def hot_swap_controller(mock_config: PipelineConfig, mock_performance_monitor: PerformanceMonitor) -> AdaptiveHotSwapController:
    """Provides a configured instance of the AdaptiveHotSwapController."""
    return AdaptiveHotSwapController(mock_config, mock_performance_monitor)

async def test_swap_to_ultra_fast_when_latency_threshold_exceeded(hot_swap_controller: AdaptiveHotSwapController, mock_performance_monitor: PerformanceMonitor):
    """
    Tests that the controller correctly identifies the need to swap to the
    ultra-fast agent when the P99 latency exceeds the configured threshold
    for several consecutive checks.
    """
    # Arrange
    hot_swap_controller.current_agent = AgentType.STANDARD
    mock_performance_monitor.get_recent_p99_latency.return_value = 150.0  # Above 100ms threshold
    hot_swap_controller.consecutive_violations = 2 # Set to be one check away from swapping

    # Act
    should_swap, trigger = hot_swap_controller.should_swap_to_ultra_fast()

    # Assert
    assert should_swap is True
    assert trigger == SwapTrigger.LATENCY_THRESHOLD
    assert hot_swap_controller.consecutive_violations == 3

async def test_no_swap_during_cooldown_period(hot_swap_controller: AdaptiveHotSwapController, mock_performance_monitor: PerformanceMonitor):
    """
    Tests that no swap is triggered, regardless of metrics, if the controller
    is within its post-swap cooldown period.
    """
    # Arrange
    hot_swap_controller.cooldown_active = True
    mock_performance_monitor.get_recent_p99_latency.return_value = 200.0 # High latency

    # Act
    should_swap, trigger = hot_swap_controller.should_swap_to_ultra_fast()

    # Assert
    assert should_swap is False
    assert trigger is None

async def test_swap_back_to_standard_on_performance_recovery(hot_swap_controller: AdaptiveHotSwapController, mock_performance_monitor: PerformanceMonitor):
    """
    Tests that the controller swaps back to the standard agent when performance
    metrics have stabilized within the configured "safe" thresholds.
    """
    # Arrange
    hot_swap_controller.current_agent = AgentType.ULTRA_FAST
    # Simulate excellent performance
    mock_performance_monitor.get_recent_p99_latency.return_value = 50.0   # Below safe threshold of 70ms
    mock_performance_monitor.get_current_throughput.return_value = 700.0 # Above safe threshold of 600
    mock_performance_monitor.get_recent_error_rate.return_value = 0.01    # Below 5%
    hot_swap_controller.recovery_confirmation_count = 4 # One check away from swapping back

    # Act
    should_swap, trigger = hot_swap_controller.should_swap_to_standard()

    # Assert
    assert should_swap is True
    assert trigger == SwapTrigger.RECOVERY_COMPLETE
    assert hot_swap_controller.recovery_confirmation_count == 5

@patch('src.pipeline_core.AgentManager', new_callable=AsyncMock)
@patch('src.pipeline_core.MarketDataGenerator', new_callable=AsyncMock)
@patch('src.pipeline_core.PerformanceMonitor', new_callable=AsyncMock)
@patch('src.pipeline_core.SystemCircuitBreaker')
@patch('src.pipeline_core.AdaptiveHotSwapController', new_callable=AsyncMock)
async def test_pipeline_initialization_and_shutdown(mock_swap_ctrl, mock_cb, mock_perf_mon, mock_data_gen, mock_agent_mgr, mock_config):
    """
    Tests the high-level start and stop logic of the main HighVelocityPipeline class,
    ensuring all components are initialized and cleaned up correctly.
    """
    # Arrange
    pipeline = HighVelocityPipeline(mock_config)

    # Mock the infinite loops to allow the test to complete
    pipeline._message_generation_loop = AsyncMock()
    pipeline._batch_processing_loop = AsyncMock()
    
    # Act
    # Run the start method but time it out, as it's designed to run forever.
    # This is enough to check that initialization logic is called.
    try:
        await asyncio.wait_for(pipeline.start(), timeout=0.1)
    except asyncio.TimeoutError:
        pass # Expected behavior

    # Assert: Check that components were initialized
    assert pipeline.is_running is True
    mock_agent_mgr.return_value.initialize.assert_awaited_once()
    mock_perf_mon.return_value.start.assert_awaited_once()

    # Act: Stop the pipeline
    await pipeline.stop()

    # Assert: Check that cleanup logic was called
    assert pipeline.is_running is False
    mock_perf_mon.return_value.stop.assert_awaited_once()
    mock_agent_mgr.return_value.cleanup.assert_awaited_once()
