"""
High-Velocity AI Pipeline - Source Package
Production-grade neural coordination system with adaptive hot-swapping
"""

__version__ = "1.0.0"
__author__ = "High-Velocity Pipeline Team"
__license__ = "MIT"

# Core imports for easy access
from .pipeline_core import HighVelocityPipeline, AdaptiveHotSwapController
from .agent_manager import AgentManager, AgentType
from .synthetic_market_data import MarketDataGenerator, MarketCondition
from .performance_monitor import PerformanceMonitor, LatencyTracker
from .config_manager import PipelineConfig, ConfigurationManager
from .circuit_breaker import CircuitBreaker, SystemCircuitBreaker

__all__ = [
    # Core pipeline
    "HighVelocityPipeline",
    "AdaptiveHotSwapController",
    
    # Agent management
    "AgentManager", 
    "AgentType",
    
    # Data generation
    "MarketDataGenerator",
    "MarketCondition",
    
    # Monitoring
    "PerformanceMonitor",
    "LatencyTracker",
    
    # Configuration
    "PipelineConfig",
    "ConfigurationManager",
    
    # Fault tolerance
    "CircuitBreaker",
    "SystemCircuitBreaker",
]