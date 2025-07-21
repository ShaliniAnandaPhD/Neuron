#!/usr/bin/env python3
"""
Configuration Manager - Centralized Configuration System
Handles pipeline configuration from multiple sources with validation

This module provides:
- Environment variable configuration
- JSON file configuration with inheritance
- Configuration validation and type checking
- Dynamic configuration updates
- Configuration export and documentation
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    """
    Comprehensive pipeline configuration
    
    All configuration parameters for the high-velocity pipeline
    with sensible defaults and validation.
    """
    
    # =============================================================================
    # API CONFIGURATION
    # =============================================================================
    openai_api_key: str = ""
    groq_api_key: str = ""
    wandb_api_key: Optional[str] = None
    
    # =============================================================================
    # PERFORMANCE THRESHOLDS
    # =============================================================================
    latency_threshold_ms: float = 100.0
    safe_latency_threshold_ms: float = 70.0
    safe_throughput_threshold: float = 600.0
    cooldown_period_seconds: float = 20.0
    
    # =============================================================================
    # TARGET PERFORMANCE
    # =============================================================================
    target_throughput: float = 800.0
    message_batch_size: int = 100
    batch_interval_seconds: float = 0.125
    
    # =============================================================================
    # AGENT CONFIGURATION
    # =============================================================================
    default_agent: str = "standard"
    max_agent_swaps: int = 50
    openai_model: str = "gpt-4-turbo-preview"
    groq_model: str = "llama3-70b-8192"
    api_timeout_seconds: float = 30.0
    api_max_retries: int = 3
    
    # =============================================================================
    # SYSTEM LIMITS
    # =============================================================================
    max_message_queue_size: int = 10000
    max_memory_usage_mb: int = 2048
    max_cpu_usage_percent: float = 80.0
    
    # =============================================================================
    # MONITORING CONFIGURATION
    # =============================================================================
    enable_csv_export: bool = True
    enable_weave_tracing: bool = True
    metrics_update_interval_seconds: float = 1.0
    export_directory: str = "exports"
    export_csv_filename: Optional[str] = None
    export_json_reports: bool = True
    
    # =============================================================================
    # CIRCUIT BREAKER SETTINGS
    # =============================================================================
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: float = 30.0
    circuit_breaker_success_threshold: int = 3
    
    # =============================================================================
    # MARKET DATA GENERATION
    # =============================================================================
    market_volatility_enabled: bool = True
    market_symbols_count: int = 12
    market_condition_change_interval_seconds: float = 30.0
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # =============================================================================
    # DEPLOYMENT SETTINGS
    # =============================================================================
    deployment_env: str = "development"
    health_check_port: int = 8080
    metrics_port: int = 8081
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 1000
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        errors = []
        
        # API keys validation
        if not self.openai_api_key:
            errors.append("OpenAI API key is required")
        if not self.groq_api_key:
            errors.append("GROQ API key is required")
        
        # Performance thresholds validation
        if self.latency_threshold_ms <= 0:
            errors.append("Latency threshold must be positive")
        if self.safe_latency_threshold_ms >= self.latency_threshold_ms:
            errors.append("Safe latency threshold must be less than latency threshold")
        if self.safe_throughput_threshold <= 0:
            errors.append("Safe throughput threshold must be positive")
        if self.cooldown_period_seconds <= 0:
            errors.append("Cooldown period must be positive")
        
        # Target performance validation
        if self.target_throughput <= 0:
            errors.append("Target throughput must be positive")
        if self.message_batch_size <= 0:
            errors.append("Message batch size must be positive")
        if self.batch_interval_seconds <= 0:
            errors.append("Batch interval must be positive")
        
        # Agent configuration validation
        if self.default_agent not in ["standard", "ultra_fast"]:
            errors.append("Default agent must be 'standard' or 'ultra_fast'")
        if self.max_agent_swaps < 0:
            errors.append("Max agent swaps must be non-negative")
        if self.api_timeout_seconds <= 0:
            errors.append("API timeout must be positive")
        if self.api_max_retries < 0:
            errors.append("API max retries must be non-negative")
        
        # System limits validation
        if self.max_message_queue_size <= 0:
            errors.append("Max message queue size must be positive")
        if self.max_memory_usage_mb <= 0:
            errors.append("Max memory usage must be positive")
        if self.max_cpu_usage_percent <= 0 or self.max_cpu_usage_percent > 100:
            errors.append("Max CPU usage must be between 0 and 100")
        
        # Monitoring configuration validation
        if self.metrics_update_interval_seconds <= 0:
            errors.append("Metrics update interval must be positive")
        
        # Circuit breaker validation
        if self.circuit_breaker_failure_threshold <= 0:
            errors.append("Circuit breaker failure threshold must be positive")
        if self.circuit_breaker_timeout_seconds <= 0:
            errors.append("Circuit breaker timeout must be positive")
        if self.circuit_breaker_success_threshold <= 0:
            errors.append("Circuit breaker success threshold must be positive")
        
        # Market data validation
        if self.market_symbols_count <= 0:
            errors.append("Market symbols count must be positive")
        if self.market_condition_change_interval_seconds <= 0:
            errors.append("Market condition change interval must be positive")
        
        # Deployment settings validation
        if not (1024 <= self.health_check_port <= 65535):
            errors.append("Health check port must be between 1024 and 65535")
        if not (1024 <= self.metrics_port <= 65535):
            errors.append("Metrics port must be between 1024 and 65535")
        if self.health_check_port == self.metrics_port:
            errors.append("Health check and metrics ports must be different")
        
        if errors:
            logger = logging.getLogger(__name__)
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                # Type conversion based on field type
                field_type = self.__dataclass_fields__[key].type
                
                # Handle Optional types
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                    # Get the non-None type from Optional[T]
                    non_none_types = [t for t in field_type.__args__ if t is not type(None)]
                    if non_none_types:
                        field_type = non_none_types[0]
                
                # Convert value to appropriate type
                try:
                    if field_type == bool:
                        # Handle string boolean values
                        if isinstance(value, str):
                            converted_value = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            converted_value = bool(value)
                    elif field_type in (int, float, str):
                        converted_value = field_type(value)
                    else:
                        converted_value = value
                    
                    setattr(self, key, converted_value)
                    
                except (ValueError, TypeError) as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to convert config value {key}={value}: {e}")
    
    @classmethod
    def load_from_env(cls) -> 'PipelineConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # Environment variable mappings
        env_mappings = {
            # API Configuration
            'OPENAI_API_KEY': 'openai_api_key',
            'GROQ_API_KEY': 'groq_api_key',
            'WANDB_API_KEY': 'wandb_api_key',
            
            # Performance Thresholds
            'PIPELINE_LATENCY_THRESHOLD_MS': 'latency_threshold_ms',
            'PIPELINE_SAFE_LATENCY_THRESHOLD_MS': 'safe_latency_threshold_ms',
            'PIPELINE_SAFE_THROUGHPUT_THRESHOLD': 'safe_throughput_threshold',
            'PIPELINE_COOLDOWN_PERIOD_SECONDS': 'cooldown_period_seconds',
            
            # Target Performance
            'PIPELINE_TARGET_THROUGHPUT': 'target_throughput',
            'PIPELINE_MESSAGE_BATCH_SIZE': 'message_batch_size',
            'PIPELINE_BATCH_INTERVAL_SECONDS': 'batch_interval_seconds',
            
            # Agent Configuration
            'PIPELINE_DEFAULT_AGENT': 'default_agent',
            'PIPELINE_MAX_AGENT_SWAPS': 'max_agent_swaps',
            'OPENAI_MODEL': 'openai_model',
            'GROQ_MODEL': 'groq_model',
            'API_TIMEOUT_SECONDS': 'api_timeout_seconds',
            'API_MAX_RETRIES': 'api_max_retries',
            
            # System Limits
            'PIPELINE_MAX_MESSAGE_QUEUE_SIZE': 'max_message_queue_size',
            'PIPELINE_MAX_MEMORY_USAGE_MB': 'max_memory_usage_mb',
            'PIPELINE_MAX_CPU_USAGE_PERCENT': 'max_cpu_usage_percent',
            
            # Monitoring Configuration
            'PIPELINE_ENABLE_CSV_EXPORT': 'enable_csv_export',
            'PIPELINE_ENABLE_WEAVE_TRACING': 'enable_weave_tracing',
            'PIPELINE_METRICS_UPDATE_INTERVAL_SECONDS': 'metrics_update_interval_seconds',
            'PIPELINE_EXPORT_DIRECTORY': 'export_directory',
            'PIPELINE_EXPORT_CSV_FILENAME': 'export_csv_filename',
            'PIPELINE_EXPORT_JSON_REPORTS': 'export_json_reports',
            
            # Circuit Breaker
            'PIPELINE_CIRCUIT_BREAKER_FAILURE_THRESHOLD': 'circuit_breaker_failure_threshold',
            'PIPELINE_CIRCUIT_BREAKER_TIMEOUT_SECONDS': 'circuit_breaker_timeout_seconds',
            'PIPELINE_CIRCUIT_BREAKER_SUCCESS_THRESHOLD': 'circuit_breaker_success_threshold',
            
            # Market Data
            'PIPELINE_MARKET_VOLATILITY_ENABLED': 'market_volatility_enabled',
            'PIPELINE_MARKET_SYMBOLS_COUNT': 'market_symbols_count',
            'PIPELINE_MARKET_CONDITION_CHANGE_INTERVAL_SECONDS': 'market_condition_change_interval_seconds',
            
            # Logging
            'PIPELINE_LOG_LEVEL': 'log_level',
            'PIPELINE_LOG_FILE': 'log_file',
            'PIPELINE_LOG_FORMAT': 'log_format',
            
            # Deployment
            'DEPLOYMENT_ENV': 'deployment_env',
            'HEALTH_CHECK_PORT': 'health_check_port',
            'METRICS_PORT': 'metrics_port',
            'ENABLE_RATE_LIMITING': 'enable_rate_limiting',
            'MAX_REQUESTS_PER_MINUTE': 'max_requests_per_minute'
        }
        
        # Load from environment
        env_config = {}
        for env_var, config_field in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                env_config[config_field] = value
        
        # Update configuration
        config.update_from_dict(env_config)
        
        return config
    
    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> 'PipelineConfig':
        """Load configuration from JSON file"""
        config = cls()
        
        try:
            with open(filepath, 'r') as f:
                file_config = json.load(f)
            
            # Flatten nested configuration
            flattened_config = cls._flatten_config(file_config)
            config.update_from_dict(flattened_config)
            
        except FileNotFoundError:
            logger = logging.getLogger(__name__)
            logger.error(f"Configuration file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid JSON in configuration file {filepath}: {e}")
            raise
        
        return config
    
    @staticmethod
    def _flatten_config(config_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested configuration dictionary"""
        flattened = {}
        
        for key, value in config_dict.items():
            # Skip metadata fields
            if key.startswith('_'):
                continue
            
            full_key = f"{prefix}_{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(PipelineConfig._flatten_config(value, full_key))
            else:
                # Map nested keys to flat field names
                mapped_key = cls._map_nested_key(full_key)
                if mapped_key:
                    flattened[mapped_key] = value
        
        return flattened
    
    @staticmethod
    def _map_nested_key(nested_key: str) -> Optional[str]:
        """Map nested configuration keys to flat field names"""
        mappings = {
            # Performance thresholds
            'performance_thresholds_latency_threshold_ms': 'latency_threshold_ms',
            'performance_thresholds_safe_latency_threshold_ms': 'safe_latency_threshold_ms',
            'performance_thresholds_safe_throughput_threshold': 'safe_throughput_threshold',
            'performance_thresholds_cooldown_period_seconds': 'cooldown_period_seconds',
            
            # Target performance
            'target_performance_target_throughput': 'target_throughput',
            'target_performance_message_batch_size': 'message_batch_size',
            'target_performance_batch_interval_seconds': 'batch_interval_seconds',
            
            # Agent configuration
            'agent_configuration_default_agent': 'default_agent',
            'agent_configuration_max_agent_swaps': 'max_agent_swaps',
            'agent_configuration_openai_model': 'openai_model',
            'agent_configuration_groq_model': 'groq_model',
            'agent_configuration_api_timeout_seconds': 'api_timeout_seconds',
            'agent_configuration_api_max_retries': 'api_max_retries',
            
            # System limits
            'system_limits_max_message_queue_size': 'max_message_queue_size',
            'system_limits_max_memory_usage_mb': 'max_memory_usage_mb',
            'system_limits_max_cpu_usage_percent': 'max_cpu_usage_percent',
            
            # Monitoring configuration
            'monitoring_configuration_enable_csv_export': 'enable_csv_export',
            'monitoring_configuration_enable_weave_tracing': 'enable_weave_tracing',
            'monitoring_configuration_metrics_update_interval_seconds': 'metrics_update_interval_seconds',
            'monitoring_configuration_export_directory': 'export_directory',
            'monitoring_configuration_export_json_reports': 'export_json_reports',
            
            # Circuit breaker settings
            'circuit_breaker_settings_circuit_breaker_failure_threshold': 'circuit_breaker_failure_threshold',
            'circuit_breaker_settings_circuit_breaker_timeout_seconds': 'circuit_breaker_timeout_seconds',
            'circuit_breaker_settings_circuit_breaker_success_threshold': 'circuit_breaker_success_threshold',
            
            # Market data generation
            'market_data_generation_market_volatility_enabled': 'market_volatility_enabled',
            'market_data_generation_market_symbols_count': 'market_symbols_count',
            'market_data_generation_market_condition_change_interval_seconds': 'market_condition_change_interval_seconds',
            
            # Logging configuration
            'logging_configuration_log_level': 'log_level',
            'logging_configuration_log_file': 'log_file',
            'logging_configuration_log_format': 'log_format',
            
            # Deployment settings
            'deployment_settings_deployment_env': 'deployment_env',
            'deployment_settings_health_check_port': 'health_check_port',
            'deployment_settings_metrics_port': 'metrics_port',
            'deployment_settings_enable_rate_limiting': 'enable_rate_limiting',
            'deployment_settings_max_requests_per_minute': 'max_requests_per_minute'
        }
        
        return mappings.get(nested_key)


class ConfigurationManager:
    """
    Advanced configuration management system
    
    Handles configuration loading, validation, updates, and export
    with support for multiple sources and inheritance.
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = Path(config_file) if config_file else None
        self.config: Optional[PipelineConfig] = None
        
        # Configuration history for rollback
        self.config_history: List[PipelineConfig] = []
        self.max_history = 10
        
    def load_config(self) -> PipelineConfig:
        """Load configuration from file and environment"""
        
        # Start with defaults
        config = PipelineConfig()
        
        # Load from file if specified
        if self.config_file and self.config_file.exists():
            try:
                file_config = PipelineConfig.load_from_file(self.config_file)
                config = file_config
                self.logger.info(f"Configuration loaded from file: {self.config_file}")
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
                self.logger.info("Using default configuration")
        
        # Override with environment variables
        env_config = PipelineConfig.load_from_env()
        config.update_from_dict(env_config.to_dict())
        
        # Validate configuration
        if not config.validate():
            raise ValueError("Configuration validation failed")
        
        # Store in history
        self._add_to_history(config)
        
        self.config = config
        self.logger.info("Configuration loaded and validated successfully")
        
        return config
    
    def get_config(self) -> PipelineConfig:
        """Get current configuration, loading if necessary"""
        if self.config is None:
            return self.load_config()
        return self.config
    
    def reload_config(self) -> PipelineConfig:
        """Reload configuration from sources"""
        self.logger.info("Reloading configuration...")
        return self.load_config()
    
    def update_config(self, updates: Dict[str, Any], validate: bool = True) -> bool:
        """Update configuration with new values"""
        if self.config is None:
            self.load_config()
        
        # Create a copy for update
        new_config = PipelineConfig()
        new_config.update_from_dict(self.config.to_dict())
        
        # Apply updates
        new_config.update_from_dict(updates)
        
        # Validate if requested
        if validate and not new_config.validate():
            self.logger.error("Configuration update failed validation")
            return False
        
        # Store old config in history
        self._add_to_history(self.config)
        
        # Apply new configuration
        self.config = new_config
        
        self.logger.info(f"Configuration updated with {len(updates)} changes")
        return True
    
    def rollback_config(self, steps: int = 1) -> bool:
        """Rollback configuration to previous version"""
        if len(self.config_history) < steps:
            self.logger.error(f"Cannot rollback {steps} steps, only {len(self.config_history)} available")
            return False
        
        # Get previous configuration
        previous_config = self.config_history[-(steps)]
        
        # Apply rollback
        self.config = previous_config
        
        # Remove rolled back configs from history
        self.config_history = self.config_history[:-(steps)]
        
        self.logger.info(f"Configuration rolled back {steps} steps")
        return True
    
    def _add_to_history(self, config: PipelineConfig):
        """Add configuration to history"""
        # Create a deep copy
        config_copy = PipelineConfig()
        config_copy.update_from_dict(config.to_dict())
        
        self.config_history.append(config_copy)
        
        # Maintain history size
        if len(self.config_history) > self.max_history:
            self.config_history = self.config_history[-self.max_history:]
    
    def export_config(self, filepath: Union[str, Path], format: str = "json") -> bool:
        """Export current configuration to file"""
        if self.config is None:
            self.logger.error("No configuration to export")
            return False
        
        try:
            filepath = Path(filepath)
            
            if format.lower() == "json":
                config_dict = self._convert_to_nested_dict(self.config.to_dict())
                
                with open(filepath, 'w') as f:
                    json.dump(config_dict, f, indent=2, default=str)
                
            elif format.lower() == "env":
                self._export_as_env_file(filepath)
            
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return False
            
            self.logger.info(f"Configuration exported to: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def _convert_to_nested_dict(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat configuration to nested structure"""
        nested = {
            "_comment": "High-Velocity AI Pipeline Configuration",
            "_exported_at": str(datetime.now()),
            "performance_thresholds": {},
            "target_performance": {},
            "agent_configuration": {},
            "system_limits": {},
            "monitoring_configuration": {},
            "circuit_breaker_settings": {},
            "market_data_generation": {},
            "logging_configuration": {},
            "deployment_settings": {}
        }
        
        # Field to section mapping
        field_mapping = {
            # Performance thresholds
            'latency_threshold_ms': ('performance_thresholds', 'latency_threshold_ms'),
            'safe_latency_threshold_ms': ('performance_thresholds', 'safe_latency_threshold_ms'),
            'safe_throughput_threshold': ('performance_thresholds', 'safe_throughput_threshold'),
            'cooldown_period_seconds': ('performance_thresholds', 'cooldown_period_seconds'),
            
            # Target performance
            'target_throughput': ('target_performance', 'target_throughput'),
            'message_batch_size': ('target_performance', 'message_batch_size'),
            'batch_interval_seconds': ('target_performance', 'batch_interval_seconds'),
            
            # Agent configuration
            'default_agent': ('agent_configuration', 'default_agent'),
            'max_agent_swaps': ('agent_configuration', 'max_agent_swaps'),
            'openai_model': ('agent_configuration', 'openai_model'),
            'groq_model': ('agent_configuration', 'groq_model'),
            'api_timeout_seconds': ('agent_configuration', 'api_timeout_seconds'),
            'api_max_retries': ('agent_configuration', 'api_max_retries'),
            
            # System limits
            'max_message_queue_size': ('system_limits', 'max_message_queue_size'),
            'max_memory_usage_mb': ('system_limits', 'max_memory_usage_mb'),
            'max_cpu_usage_percent': ('system_limits', 'max_cpu_usage_percent'),
            
            # Monitoring
            'enable_csv_export': ('monitoring_configuration', 'enable_csv_export'),
            'enable_weave_tracing': ('monitoring_configuration', 'enable_weave_tracing'),
            'metrics_update_interval_seconds': ('monitoring_configuration', 'metrics_update_interval_seconds'),
            'export_directory': ('monitoring_configuration', 'export_directory'),
            'export_json_reports': ('monitoring_configuration', 'export_json_reports'),
            
            # Circuit breaker
            'circuit_breaker_failure_threshold': ('circuit_breaker_settings', 'circuit_breaker_failure_threshold'),
            'circuit_breaker_timeout_seconds': ('circuit_breaker_settings', 'circuit_breaker_timeout_seconds'),
            'circuit_breaker_success_threshold': ('circuit_breaker_settings', 'circuit_breaker_success_threshold'),
            
            # Market data
            'market_volatility_enabled': ('market_data_generation', 'market_volatility_enabled'),
            'market_symbols_count': ('market_data_generation', 'market_symbols_count'),
            'market_condition_change_interval_seconds': ('market_data_generation', 'market_condition_change_interval_seconds'),
            
            # Logging
            'log_level': ('logging_configuration', 'log_level'),
            'log_file': ('logging_configuration', 'log_file'),
            'log_format': ('logging_configuration', 'log_format'),
            
            # Deployment
            'deployment_env': ('deployment_settings', 'deployment_env'),
            'health_check_port': ('deployment_settings', 'health_check_port'),
            'metrics_port': ('deployment_settings', 'metrics_port'),
            'enable_rate_limiting': ('deployment_settings', 'enable_rate_limiting'),
            'max_requests_per_minute': ('deployment_settings', 'max_requests_per_minute')
        }
        
        # Map fields to nested structure
        for field_name, value in flat_dict.items():
            if field_name in field_mapping:
                section, key = field_mapping[field_name]
                nested[section][key] = value
        
        return nested
    
    def _export_as_env_file(self, filepath: Path):
        """Export configuration as environment file"""
        config_dict = self.config.to_dict()
        
        with open(filepath, 'w') as f:
            f.write("# High-Velocity AI Pipeline - Environment Configuration\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            
            # Group by category
            categories = {
                "API Configuration": ['openai_api_key', 'groq_api_key', 'wandb_api_key'],
                "Performance Thresholds": ['latency_threshold_ms', 'safe_latency_threshold_ms', 'safe_throughput_threshold', 'cooldown_period_seconds'],
                "Target Performance": ['target_throughput', 'message_batch_size', 'batch_interval_seconds'],
                "Agent Configuration": ['default_agent', 'max_agent_swaps', 'openai_model', 'groq_model', 'api_timeout_seconds', 'api_max_retries']
            }
            
            for category, fields in categories.items():
                f.write(f"# {category}\n")
                for field in fields:
                    if field in config_dict:
                        env_var = self._field_to_env_var(field)
                        value = config_dict[field]
                        if isinstance(value, str) and not value:
                            value = "your-key-here"
                        f.write(f"{env_var}={value}\n")
                f.write("\n")
    
    def _field_to_env_var(self, field_name: str) -> str:
        """Convert field name to environment variable name"""
        # Simple mapping for common fields
        mappings = {
            'openai_api_key': 'OPENAI_API_KEY',
            'groq_api_key': 'GROQ_API_KEY',
            'wandb_api_key': 'WANDB_API_KEY',
            'latency_threshold_ms': 'PIPELINE_LATENCY_THRESHOLD_MS',
            'target_throughput': 'PIPELINE_TARGET_THROUGHPUT'
        }
        
        if field_name in mappings:
            return mappings[field_name]
        
        # Generic conversion
        return f"PIPELINE_{field_name.upper()}"
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring"""
        if self.config is None:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "source_file": str(self.config_file) if self.config_file else None,
            "validation_status": "valid" if self.config.validate() else "invalid",
            "key_settings": {
                "latency_threshold_ms": self.config.latency_threshold_ms,
                "target_throughput": self.config.target_throughput,
                "default_agent": self.config.default_agent,
                "deployment_env": self.config.deployment_env
            },
            "history_count": len(self.config_history),
            "last_updated": datetime.now().isoformat()
        }


# Convenience functions
def get_config() -> PipelineConfig:
    """Get configuration from default sources"""
    return PipelineConfig.load_from_env()


def load_config_from_file(filepath: Union[str, Path]) -> PipelineConfig:
    """Load configuration from specific file"""
    return PipelineConfig.load_from_file(filepath)