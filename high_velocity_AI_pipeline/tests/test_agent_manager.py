#!/usr/bin/env python3
"""
Unit Tests for Agent Manager (src/agent_manager.py)

This test suite verifies the functionality of the AgentManager and its associated
agents (StandardAgent, UltraFastAgent). It uses mocking to isolate the components
and simulate API interactions.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add src to path to allow direct import of modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_manager import AgentManager, AgentType, StandardAgent, UltraFastAgent, AgentHealth, AgentResponse
from src.config_manager import PipelineConfig
from src.synthetic_market_data import MarketMessage, MarketCondition

# Pytest marker for asyncio tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_config() -> PipelineConfig:
    """Provides a mock PipelineConfig object for testing."""
    config = MagicMock(spec=PipelineConfig)
    config.openai_api_key = "fake_openai_key_for_testing"
    config.groq_api_key = "fake_groq_key_for_testing"
    config.openai_model = "gpt-4-test-model"
    config.groq_model = "llama3-test-model"
    config.api_timeout_seconds = 5.0
    config.api_max_retries = 2
    return config

@pytest.fixture
def mock_market_message() -> MarketMessage:
    """Provides a mock MarketMessage for testing."""
    return MarketMessage(
        message_id="test-msg-12345",
        symbol="TESTCO",
        price=150.75,
        volume=12000,
        timestamp=datetime.now(),
        market_condition=MarketCondition.STABLE,
        change_percent=0.5,
        bid_ask_spread=0.02,
        high_24h=152.0,
        low_24h=149.5,
        volume_24h=100000
    )

@patch('openai.AsyncOpenAI')
def test_standard_agent_initialization(mock_openai_client, mock_config):
    """Tests that the StandardAgent initializes its client correctly."""
    # Act
    agent = StandardAgent(mock_config)
    # Assert
    mock_openai_client.assert_called_with(
        api_key=mock_config.openai_api_key,
        timeout=mock_config.api_timeout_seconds,
        max_retries=mock_config.api_max_retries
    )
    assert agent.model == mock_config.openai_model

@patch('httpx.AsyncClient')
def test_ultra_fast_agent_initialization(mock_httpx_client, mock_config):
    """Tests that the UltraFastAgent initializes its client correctly."""
    # Act
    agent = UltraFastAgent(mock_config)
    # Assert
    mock_httpx_client.assert_called_with(
        base_url="https://api.groq.com/openai/v1",
        headers={"Authorization": f"Bearer {mock_config.groq_api_key}"},
        timeout=mock_config.api_timeout_seconds
    )
    assert agent.model == mock_config.groq_model

async def test_agent_manager_routing_and_fallback(mock_config, mock_market_message):
    """
    Tests the AgentManager's core logic:
    1. Correctly routes to the preferred agent.
    2. Falls back to a healthy agent if the preferred one fails.
    """
    # Arrange
    agent_manager = AgentManager(mock_config)

    # Mock the process_message methods for both agents
    successful_response = AgentResponse(success=True, data={"analysis": "buy"}, processing_time_ms=50.0, agent_type=AgentType.ULTRA_FAST)
    failed_response = AgentResponse(success=False, data=None, processing_time_ms=500.0, agent_type=AgentType.STANDARD, error_message="API Error")

    agent_manager.agents[AgentType.STANDARD].process_message = AsyncMock(return_value=failed_response)
    agent_manager.agents[AgentType.ULTRA_FAST].process_message = AsyncMock(return_value=successful_response)

    # Mock health status to ensure both agents are initially considered healthy
    agent_manager.health_status = {
        AgentType.STANDARD: AgentHealth(agent_type=AgentType.STANDARD, is_healthy=True, last_check=datetime.now(), response_time_ms=120.0, error_rate=0.0, total_requests=10, successful_requests=10, consecutive_failures=0),
        AgentType.ULTRA_FAST: AgentHealth(agent_type=AgentType.ULTRA_FAST, is_healthy=True, last_check=datetime.now(), response_time_ms=40.0, error_rate=0.0, total_requests=10, successful_requests=10, consecutive_failures=0)
    }

    # --- Act & Assert: Test Fallback ---
    # Prefer the standard agent, which is mocked to fail
    response = await agent_manager.process_message(mock_market_message, preferred_agent=AgentType.STANDARD)

    # Assert that the standard agent was tried first
    agent_manager.agents[AgentType.STANDARD].process_message.assert_called_once_with(mock_market_message)
    # Assert that the manager fell back to the ultra-fast agent
    agent_manager.agents[AgentType.ULTRA_FAST].process_message.assert_called_once_with(mock_market_message)
    # Assert the final response is the successful one from the fallback agent
    assert response.success is True
    assert response.agent_type == AgentType.ULTRA_FAST

async def test_agent_manager_no_healthy_agents(mock_config, mock_market_message):
    """Tests that the AgentManager returns a failure if no agents are healthy."""
    # Arrange
    agent_manager = AgentManager(mock_config)

    # Mock both agents to be unhealthy
    agent_manager.health_status = {
        AgentType.STANDARD: AgentHealth(agent_type=AgentType.STANDARD, is_healthy=False, last_check=datetime.now(), response_time_ms=5000.0, error_rate=1.0, total_requests=10, successful_requests=0, consecutive_failures=10),
        AgentType.ULTRA_FAST: AgentHealth(agent_type=AgentType.ULTRA_FAST, is_healthy=False, last_check=datetime.now(), response_time_ms=5000.0, error_rate=1.0, total_requests=10, successful_requests=0, consecutive_failures=10)
    }
    
    # Mock process_message to ensure they are not even called
    agent_manager.agents[AgentType.STANDARD].process_message = AsyncMock()
    agent_manager.agents[AgentType.ULTRA_FAST].process_message = AsyncMock()

    # Act
    response = await agent_manager.process_message(mock_market_message, preferred_agent=AgentType.STANDARD)

    # Assert
    assert response.success is False
    assert response.error_message == "All agents unavailable"
    # Ensure no agent processing was attempted
    agent_manager.agents[AgentType.STANDARD].process_message.assert_not_called()
    agent_manager.agents[AgentType.ULTRA_FAST].process_message.assert_not_called()
