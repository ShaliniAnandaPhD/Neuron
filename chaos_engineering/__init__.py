"""
AI Agent Chaos Engineering Test Suite

A production-ready framework for testing AI agent resilience through chaos engineering.
"""

__version__ = "1.0.0"
__author__ = "AI Resilience Team"

from .agent import Agent, AgentPool, AgentState, Task
from .chaos_injector import ChaosInjector, ChaosType, ChaosEvent
from .monitor import HealthMonitor, HealthStatus, HealthMetrics, FailureEvent
from .orchestrator import RecoveryOrchestrator, RecoveryStrategy, RecoveryEvent
from .metrics import MetricsCollector, TestResult, TestReporter
from .test_scenarios import TestScenario, get_scenario, SCENARIOS

__all__ = [
    # Agent components
    "Agent",
    "AgentPool", 
    "AgentState",
    "Task",
    
    # Chaos injection
    "ChaosInjector",
    "ChaosType",
    "ChaosEvent",
    
    # Monitoring
    "HealthMonitor",
    "HealthStatus",
    "HealthMetrics",
    "FailureEvent",
    
    # Recovery
    "RecoveryOrchestrator",
    "RecoveryStrategy",
    "RecoveryEvent",
    
    # Metrics and reporting
    "MetricsCollector",
    "TestResult",
    "TestReporter",
    
    # Test scenarios
    "TestScenario",
    "get_scenario",
    "SCENARIOS",
]