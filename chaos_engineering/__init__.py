"""
AI Agent Chaos Engineering Test Suite

A production-ready framework for testing AI agent resilience through chaos engineering.
"""

__version__ = "1.0.0"
__author__ = "AI Resilience Team"

import os
import sys

# agent.py lives here and the other modules live in "health states/", and
# they import each other as top-level modules (`from agent import AgentPool`).
# Make both folders importable (appended, so they never shadow other packages).
_here = os.path.dirname(os.path.abspath(__file__))
for _folder in (_here, os.path.join(_here, "health states")):
    if _folder not in sys.path:
        sys.path.append(_folder)

from agent import Agent, AgentPool, AgentState, Task  # noqa: E402
from chaos_injector import ChaosEvent, ChaosInjector, ChaosType  # noqa: E402
from metrics import MetricsCollector, TestReporter, TestResult  # noqa: E402
from monitor import FailureEvent, HealthMetrics, HealthMonitor, HealthStatus  # noqa: E402
from orchestrator import RecoveryEvent, RecoveryOrchestrator, RecoveryStrategy  # noqa: E402
from test_scenarios import SCENARIOS, TestScenario, get_scenario  # noqa: E402

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