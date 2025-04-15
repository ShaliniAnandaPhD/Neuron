"""
config.py - Configuration Management for Neuron Framework

This module handles loading, validating, and providing access to configuration
values throughout the Neuron framework. It supports multiple configuration
sources (files, environment variables, direct settings) with proper precedence.

The configuration system is designed to be flexible and extensible, allowing
for different configuration strategies in different environments.
"""

import json
import logging
import os
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    # Core system settings
    "system": {
        "log_level": "INFO",
        "environment": "development",
        "max_threads": 8,
        "persistence_enabled": True,
        "data_dir": "./data",
        "plugin_dir": "./plugins",
    },
    
    # Agent settings
    "agent": {
        "default_timeout": 30.0,  # seconds
        "max_message_size": 1048576,  # 1MB
        "retry_attempts": 3,
        "memory_limit": 104857600,  # 100MB per agent
    },
    
    # SynapticBus settings
    "synaptic_bus": {
        "message_ttl": 3600,  # seconds
        "max_queue_size": 10000,
        "delivery_guarantees": "at_least_once",
        "channel_buffer_size": 1000,
    },
    
    # Memory settings
    "memory": {
        "working_memory_capacity": 100,
        "episodic_memory_ttl": 86400,  # 1 day in seconds
        "importance_threshold": 0.3,  # Memories below this can be forgotten
        "forgetting_strategy": "least_important_first",
    },
    
    # Circuit settings
    "circuit": {
        "validation_level": "strict",
        "auto_recovery": True,
        "max_circuit_size": 100,  # maximum number of agents per circuit
    },
    
    # Monitoring settings
    "monitoring": {
        "enabled": True,
        "metrics_interval": 10.0,  # seconds
        "health_check_interval": 60.0,  # seconds
        "retention_period": 86400,  # 1 day in seconds
    },
    
    # Extension settings
    "extensions": {
        "auto_discover": True,
        "allowed_plugins": ["*"],  # "*" means all plugins are allowed
    }
}


@dataclass
class NeuronConfig:
    """
    Configuration manager for the Neuron framework.
    
    This class provides a unified interface to access configuration values
    from multiple sources with proper precedence:
    1. Direct settings (highest precedence)
    2. Environment variables (format: NEURON_SECTION_KEY)
    3. Configuration files
    4. Default values (lowest precedence)
    
    It also handles validation, type conversion, and provides a consistent
    API for accessing configuration throughout the application.
    """
    
    # The actual configuration data, initialized with defaults
    _config: Dict[str, Any] = field(default_factory=lambda: deepcopy(DEFAULT_CONFIG))
    
    # Paths to configuration files that have been loaded
    _loaded_files: List[Path] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize by loading from default locations if they exist."""
        # Check standard locations for config files
        default_locations = [
            Path("./neuron.json"),
            Path("./config/neuron.json"),
            Path(os.environ.get("NEURON_CONFIG_PATH", "")),
            Path.home() / ".neuron" / "config.json",
        ]
        
        for path in default_locations:
            if path.exists() and path.is_file():
                try:
                    self.load_file(path)
                except Exception as e:
                    logger.warning(f"Could not load config from {path}: {e}")
        
        # Load configuration from environment variables
        self._load_from_env()
    
    def load_file(self, path: Union[str, Path]) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            path: Path to the configuration file
            
        Raises:
            ConfigurationError: If the file cannot be read or parsed
        """
        path = Path(path)
        try:
            with open(path, 'r') as f:
                config_data = json.load(f)
            
            # Merge the loaded config with existing config
            self._merge_config(config_data)
            self._loaded_files.append(path.absolute())
            logger.info(f"Loaded configuration from {path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Error parsing config file {path}: {e}")
        except OSError as e:
            raise ConfigurationError(f"Error reading config file {path}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        Environment variables should be in the format NEURON_SECTION_KEY.
        For example, NEURON_SYSTEM_LOG_LEVEL would set config["system"]["log_level"].
        """
        prefix = "NEURON_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and split into parts
                parts = key[len(prefix):].lower().split('_')
                
                if len(parts) >= 2:
                    section = parts[0]
                    setting = '_'.join(parts[1:])
                    
                    # Create section if it doesn't exist
                    if section not in self._config:
                        self._config[section] = {}
                    
                    # Convert value to appropriate type based on existing config
                    if section in self._config and setting in self._config[section]:
                        existing_value = self._config[section][setting]
                        if isinstance(existing_value, bool):
                            value = value.lower() in ('true', 'yes', '1')
                        elif isinstance(existing_value, int):
                            value = int(value)
                        elif isinstance(existing_value, float):
                            value = float(value)
                    
                    # Set the value
                    self._config[section][setting] = value
                    logger.debug(f"Loaded config from environment: {section}.{setting}")
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration data with existing configuration.
        
        Args:
            new_config: New configuration to merge
        """
        for section, section_data in new_config.items():
            if section not in self._config:
                self._config[section] = {}
            
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    self._config[section][key] = value
            else:
                logger.warning(f"Ignoring non-dict section data for {section}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within the section
            default: Default value if not found
            
        Returns:
            The configuration value or default if not found
        """
        if section in self._config and key in self._config[section]:
            return self._config[section][key]
        return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Configuration section name
            
        Returns:
            Dictionary containing all keys and values in the section,
            or an empty dictionary if the section doesn't exist
        """
        return self._config.get(section, {}).copy()
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within the section
            value: Value to set
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration with a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration updates
        """
        self._merge_config(config_dict)
    
    def validate(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation errors, or empty list if valid
        """
        errors = []
        
        # Validate required sections
        required_sections = ["system", "agent", "synaptic_bus", "memory", "circuit", "monitoring"]
        for section in required_sections:
            if section not in self._config:
                errors.append(f"Missing required configuration section: {section}")
        
        # Example validation for specific settings
        if "system" in self._config:
            system = self._config["system"]
            
            # Validate log level
            valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if "log_level" in system and system["log_level"].upper() not in valid_log_levels:
                errors.append(f"Invalid log level: {system['log_level']}")
            
            # Validate max_threads
            if "max_threads" in system and not isinstance(system["max_threads"], int):
                errors.append("max_threads must be an integer")
            elif "max_threads" in system and system["max_threads"] < 1:
                errors.append("max_threads must be at least 1")
        
        # Add more specific validations as needed
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return deepcopy(self._config)
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"NeuronConfig(loaded_files={self._loaded_files})"
    
    @property
    def loaded_files(self) -> List[Path]:
        """Get the list of loaded configuration files."""
        return self._loaded_files.copy()


# Global configuration instance
# This provides a singleton-like access to configuration throughout the framework
config = NeuronConfig()


def get_config() -> NeuronConfig:
    """
    Get the global configuration instance.
    
    This function is the recommended way to access configuration
    throughout the Neuron framework.
    
    Returns:
        The global NeuronConfig instance
    """
    return config


def initialize_config(config_path: Optional[Union[str, Path]] = None,
                      config_dict: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize the global configuration.
    
    This function should be called early in application startup to
    ensure proper configuration is loaded.
    
    Args:
        config_path: Optional path to a configuration file
        config_dict: Optional dictionary with configuration overrides
        
    Raises:
        ConfigurationError: If there are validation errors
    """
    global config
    
    if config_path:
        config.load_file(config_path)
    
    if config_dict:
        config.update(config_dict)
    
    # Load from environment variables (will override file settings)
    config._load_from_env()
    
    # Validate the configuration
    errors = config.validate()
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(errors)
        raise ConfigurationError(error_msg)
    
    # Set up logging based on configuration
    log_level = config.get("system", "log_level", "INFO").upper()
    logging.root.setLevel(log_level)
    logger.info(f"Initialized configuration with log level {log_level}")


def reset_config() -> None:
    """
    Reset the global configuration to defaults.
    
    This is primarily useful for testing and for situations where
    a clean configuration state is needed.
    """
    global config
    config = NeuronConfig()
    logger.info("Reset configuration to defaults")
"""
