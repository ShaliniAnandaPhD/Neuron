#!/usr/bin/env python3
"""
Unit Tests for Configuration Manager (src/config_manager.py)

This test suite verifies the configuration loading from different sources
(environment variables, files), validation logic, and the functionality
of the ConfigurationManager class.
"""

import pytest
import os
import json
from pathlib import Path

# Add src to path to allow direct import of modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_manager import PipelineConfig, ConfigurationManager

@pytest.fixture
def cleanup_env_vars():
    """Fixture to clean up environment variables after a test."""
    # This is a generator-based fixture. Code before `yield` is setup,
    # and code after `yield` is teardown.
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)

def test_load_from_env(cleanup_env_vars):
    """
    Tests that the PipelineConfig dataclass correctly loads and type-converts
    values from environment variables.
    """
    # Arrange: Set environment variables with various types
    os.environ['OPENAI_API_KEY'] = 'env_openai_key_test'
    os.environ['GROQ_API_KEY'] = 'env_groq_key_test'
    os.environ['PIPELINE_TARGET_THROUGHPUT'] = '999.5' # Should be float
    os.environ['PIPELINE_MESSAGE_BATCH_SIZE'] = '123' # Should be int
    os.environ['PIPELINE_ENABLE_CSV_EXPORT'] = 'false' # Should be bool
    os.environ['PIPELINE_DEFAULT_AGENT'] = 'ultra_fast' # Should be string

    # Act
    config = PipelineConfig.load_from_env()

    # Assert
    assert config.openai_api_key == 'env_openai_key_test'
    assert config.groq_api_key == 'env_groq_key_test'
    assert isinstance(config.target_throughput, float) and config.target_throughput == 999.5
    assert isinstance(config.message_batch_size, int) and config.message_batch_size == 123
    assert isinstance(config.enable_csv_export, bool) and config.enable_csv_export is False
    assert config.default_agent == 'ultra_fast'

def test_load_from_file(tmp_path: Path):
    """
    Tests loading a hierarchical JSON configuration file and ensuring
    the values are correctly flattened and applied to the config object.
    """
    # Arrange: Create a temporary JSON config file
    config_content = {
        "agent_configuration": {
            "default_agent": "ultra_fast",
            "max_agent_swaps": 25
        },
        "performance_thresholds": {
            "latency_threshold_ms": 123.4
        }
    }
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(config_content))

    # Act
    config = PipelineConfig.load_from_file(config_file)

    # Assert
    assert config.default_agent == "ultra_fast"
    assert config.max_agent_swaps == 25
    assert config.latency_threshold_ms == 123.4

def test_config_validation_logic():
    """
    Tests the validation method within the PipelineConfig class to ensure it
    catches common configuration errors.
    """
    # Arrange: Start with a valid default config
    config = PipelineConfig(
        openai_api_key="fake_key",
        groq_api_key="fake_key"
    )
    # Assert: A valid config should pass validation
    assert config.validate() is True

    # --- Test invalid configurations ---
    
    # Case 1: Missing required API key
    config.openai_api_key = ""
    assert config.validate() is False
    config.openai_api_key = "fake_key" # Reset for next test

    # Case 2: Inverted latency thresholds
    config.safe_latency_threshold_ms = 200.0
    config.latency_threshold_ms = 100.0  # Safe threshold cannot be greater
    assert config.validate() is False
    config.safe_latency_threshold_ms = 70.0 # Reset
    config.latency_threshold_ms = 100.0 # Reset

    # Case 3: Invalid agent name
    config.default_agent = "invalid_agent"
    assert config.validate() is False

def test_config_manager_update_and_rollback():
    """
    Tests the dynamic update and rollback functionality of the
    ConfigurationManager, ensuring state is managed correctly.
    """
    # Arrange
    manager = ConfigurationManager()
    # Load initial config (will be from defaults/empty env)
    initial_config = manager.get_config()
    initial_swaps_value = initial_config.max_agent_swaps

    # Act 1: Update the configuration
    update_success = manager.update_config({"max_agent_swaps": 99})

    # Assert 1: The update was successful and the value changed
    assert update_success is True
    assert manager.get_config().max_agent_swaps == 99

    # Act 2: Roll back the configuration
    rollback_success = manager.rollback_config()

    # Assert 2: The rollback was successful and the value is restored
    assert rollback_success is True
    assert manager.get_config().max_agent_swaps == initial_swaps_value
