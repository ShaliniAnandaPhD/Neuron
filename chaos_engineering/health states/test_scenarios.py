"""
test_scenarios.py - Predefined Test Scenarios

Collection of chaos engineering test scenarios for different failure patterns.
"""

import asyncio
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from agent import AgentPool, Task
from chaos_injector import ChaosInjector, ChaosType
from monitor import HealthMonitor
from orchestrator import RecoveryOrchestrator
from metrics import MetricsCollector, TestResult

import logging
logger = logging.getLogger(__name__)


@dataclass
class ScenarioConfig:
    """Configuration for a test scenario"""
    name: str
    description: str
    duration_seconds: float
    task_count: int
    task_rate: float  # Tasks per second
    chaos_params: Dict[str, Any]
    success_criteria: Dict[str, float]


class TestScenario(ABC):
    """Base class for test scenarios"""
    
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.agent_pool: Optional[AgentPool] = None
        self.chaos_injector: Optional[ChaosInjector] = None
        self.monitor: Optional[HealthMonitor] = None
        self.orchestrator: Optional[RecoveryOrchestrator] = None
        self.metrics: Optional[MetricsCollector] = None
        
        # Task generation
        self.submitted_tasks: List[Task] = []
        self.completed_tasks: List[Task] = []
        self._task_generator_task: Optional[asyncio.Task] = None
    
    async def setup(self, components: Dict[str, Any]):
        """Setup scenario with components"""
        self.agent_pool = components["agent_pool"]
        self.chaos_injector = components["chaos_injector"]
        self.monitor = components["monitor"]
        self.orchestrator = components["orchestrator"]
        self.metrics = components["metrics"]
        
        # Setup task completion tracking
        for agent in self.agent_pool.agents.values():
            agent.on_task_complete = self._on_task_complete
    
    async def run(self) -> TestResult:
        """Run the test scenario"""
        logger.info(f"Starting scenario: {self.config.name}")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Start task generation
            self._task_generator_task = asyncio.create_task(self._generate_tasks())
            
            # Execute scenario-specific chaos
            await self.inject_chaos()
            
            # Wait for scenario duration
            await asyncio.sleep(self.config.duration_seconds)
            
            # Stop task generation
            self._task_generator_task.cancel()
            
            # Wait for remaining tasks to complete
            await self._wait_for_completion()
            
        except Exception as e:
            logger.error(f"Scenario error: {e}")
            raise
        
        finally:
            # Calculate results
            result = await self._calculate_results(start_time)
            return result
    
    @abstractmethod
    async def inject_chaos(self):
        """Inject scenario-specific chaos"""
        pass
    
    async def _generate_tasks(self):
        """Generate tasks at specified rate"""
        task_interval = 1.0 / self.config.task_rate
        
        while len(self.submitted_tasks) < self.config.task_count:
            try:
                # Create task
                task = Task(
                    name=f"{self.config.name}-{len(self.submitted_tasks)+1}",
                    payload={"scenario": self.config.name}
                )
                
                # Submit to random healthy agent
                healthy_agents = await self.agent_pool.get_healthy_agents()
                if healthy_agents:
                    agent = random.choice(healthy_agents)
                    if await agent.submit_task(task):
                        self.submitted_tasks.append(task)
                        await self.metrics.record_counter("tasks_submitted", labels={"scenario": self.config.name})
                
                await asyncio.sleep(task_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task generation error: {e}")
    
    async def _on_task_complete(self, agent, task):
        """Track task completion"""
        self.completed_tasks.append(task)
        await self.metrics.record_counter("tasks_completed", labels={"scenario": self.config.name})
    
    async def _wait_for_completion(self):
        """Wait for tasks to complete or timeout"""
        timeout = 30  # 30 second timeout
        start = asyncio.get_event_loop().time()
        
        while len(self.completed_tasks) < len(self.submitted_tasks):
            if asyncio.get_event_loop().time() - start > timeout:
                logger.warning("Task completion timeout reached")
                break
            await asyncio.sleep(0.5)
    
    async def _calculate_results(self, start_time: float) -> TestResult:
        """Calculate test results"""
        end_time = asyncio.get_event_loop().time()
        
        # Get metrics from components
        detection_stats = await self.monitor.get_failure_detection_stats()
        recovery_stats = await self.orchestrator.get_recovery_stats()
        
        # Calculate data integrity
        total_tasks = len(self.submitted_tasks)
        completed_tasks = len(self.completed_tasks)
        lost_tasks = total_tasks - completed_tasks
        data_integrity = completed_tasks / total_tasks if total_tasks > 0 else 1.0
        
        # Build result
        result = TestResult(
            test_id=f"{self.config.name}_{int(start_time)}",
            scenario=self.config.name,
            start_time=asyncio.get_event_loop().time(),
            end_time=asyncio.get_event_loop().time(),
            success=True,  # Will be updated based on criteria
            failure_detection_time=detection_stats["average_detection_time"],
            recovery_time=recovery_stats["average_recovery_time"],
            data_integrity=data_integrity,
            detection_threshold=self.config.success_criteria["detection_time"],
            recovery_threshold=self.config.success_criteria["recovery_time"],
            integrity_threshold=self.config.success_criteria["data_integrity"],
            metrics={
                "total_processed": completed_tasks,
                "total_lost": lost_tasks,
                "detection_stats": detection_stats,
                "recovery_stats": recovery_stats,
                "duration": end_time - start_time
            }
        )
        
        # Check success criteria
        result.success = (
            result.detection_passed and
            result.recovery_passed and
            result.integrity_passed
        )
        
        return result


class CascadeFailureScenario(TestScenario):
    """Multiple agents fail in cascade"""
    
    async def inject_chaos(self):
        """Inject cascading failures"""
        await self.chaos_injector.inject_chaos(
            ChaosType.CASCADE_FAILURE,
            duration_seconds=self.config.duration_seconds * 0.5,
            **self.config.chaos_params
        )


class NetworkPartitionScenario(TestScenario):
    """Network split between agent groups"""
    
    async def inject_chaos(self):
        """Inject network partition"""
        await self.chaos_injector.inject_chaos(
            ChaosType.NETWORK_PARTITION,
            duration_seconds=self.config.duration_seconds * 0.6,
            partition_groups=self.config.chaos_params.get("partition_groups", 2)
        )


class ResourceExhaustionScenario(TestScenario):
    """Memory and CPU pressure"""
    
    async def inject_chaos(self):
        """Inject resource exhaustion"""
        # Memory pressure
        memory_task = asyncio.create_task(
            self.chaos_injector.inject_chaos(
                ChaosType.MEMORY_LEAK,
                duration_seconds=self.config.duration_seconds * 0.7,
                target_mb=self.config.chaos_params.get("memory_mb", 100)
            )
        )
        
        # CPU throttling
        cpu_task = asyncio.create_task(
            self.chaos_injector.inject_chaos(
                ChaosType.CPU_THROTTLE,
                duration_seconds=self.config.duration_seconds * 0.7,
                cpu_percent=self.config.chaos_params.get("cpu_percent", 50)
            )
        )
        
        await asyncio.gather(memory_task, cpu_task)


class SlowDeathScenario(TestScenario):
    """Gradual degradation of agents"""
    
    async def inject_chaos(self):
        """Inject slow degradation"""
        await self.chaos_injector.inject_chaos(
            ChaosType.SLOW_DEATH,
            duration_seconds=self.config.duration_seconds * 0.8,
            degradation_rate=self.config.chaos_params.get("degradation_rate", 0.05)
        )


# Predefined scenario configurations
SCENARIOS = {
    "cascade-failure": ScenarioConfig(
        name="cascade-failure",
        description="Tests recovery from cascading agent failures",
        duration_seconds=60,
        task_count=100,
        task_rate=2.0,
        chaos_params={
            "initial_failures": 2,
            "cascade_probability": 0.5,
            "cascade_delay": 2.0
        },
        success_criteria={
            "detection_time": 1.0,
            "recovery_time": 2.0,
            "data_integrity": 1.0
        }
    ),
    
    "network-partition": ScenarioConfig(
        name="network-partition",
        description="Tests handling of network splits",
        duration_seconds=60,
        task_count=80,
        task_rate=1.5,
        chaos_params={
            "partition_groups": 2
        },
        success_criteria={
            "detection_time": 1.5,
            "recovery_time": 3.0,
            "data_integrity": 0.95
        }
    ),
    
    "resource-exhaustion": ScenarioConfig(
        name="resource-exhaustion",
        description="Tests behavior under resource pressure",
        duration_seconds=90,
        task_count=120,
        task_rate=1.5,
        chaos_params={
            "memory_mb": 200,
            "cpu_percent": 25
        },
        success_criteria={
            "detection_time": 2.0,
            "recovery_time": 5.0,
            "data_integrity": 0.90
        }
    ),
    
    "slow-death": ScenarioConfig(
        name="slow-death",
        description="Tests detection and recovery from gradual degradation",
        duration_seconds=120,
        task_count=150,
        task_rate=1.25,
        chaos_params={
            "degradation_rate": 0.02,
            "target_agents": 3
        },
        success_criteria={
            "detection_time": 3.0,
            "recovery_time": 5.0,
            "data_integrity": 0.95
        }
    )
}


def get_scenario(name: str) -> TestScenario:
    """Get a test scenario by name"""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")
    
    config = SCENARIOS[name]
    
    if name == "cascade-failure":
        return CascadeFailureScenario(config)
    elif name == "network-partition":
        return NetworkPartitionScenario(config)
    elif name == "resource-exhaustion":
        return ResourceExhaustionScenario(config)
    elif name == "slow-death":
        return SlowDeathScenario(config)
    else:
        raise ValueError(f"Scenario not implemented: {name}")