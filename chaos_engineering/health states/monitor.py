"""
monitor.py - Health Monitoring and Detection

Real-time monitoring system for detecting failures and triggering recovery.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics

from agent import Agent, AgentState, AgentPool

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Overall system health status"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"


@dataclass
class HealthMetrics:
    """System health metrics"""
    timestamp: datetime
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    failed_agents: int
    average_queue_size: float
    average_response_time: float
    error_rate: float
    
    @property
    def health_score(self) -> float:
        """Calculate overall health score (0-1)"""
        if self.total_agents == 0:
            return 0.0
        
        # Weight different factors
        agent_health = self.healthy_agents / self.total_agents
        queue_health = 1.0 / (1.0 + self.average_queue_size / 10)  # Penalize long queues
        error_health = 1.0 - self.error_rate
        
        # Weighted average
        return (agent_health * 0.5 + queue_health * 0.3 + error_health * 0.2)
    
    @property
    def status(self) -> HealthStatus:
        """Determine overall health status"""
        score = self.health_score
        if score >= 0.8:
            return HealthStatus.HEALTHY
        elif score >= 0.6:
            return HealthStatus.DEGRADED
        elif score >= 0.3:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED


@dataclass
class FailureEvent:
    """Record of a detected failure"""
    timestamp: datetime
    agent_id: str
    failure_type: str
    detection_time: float  # Time to detect in seconds
    details: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Monitors system health and detects failures in real-time.
    """
    
    def __init__(
        self,
        agent_pool: AgentPool,
        check_interval: float = 0.5,
        failure_threshold: float = 1.0,  # 1 second detection target
        history_window: int = 100
    ):
        self.agent_pool = agent_pool
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.history_window = history_window
        
        # Monitoring state
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_check_time = time.time()
        
        # Agent state tracking
        self._agent_states: Dict[str, AgentState] = {}
        self._agent_last_heartbeat: Dict[str, float] = {}
        self._agent_failure_start: Dict[str, float] = {}
        
        # Metrics history
        self.metrics_history: List[HealthMetrics] = []
        self.failure_events: List[FailureEvent] = []
        
        # Callbacks
        self.on_failure_detected: Optional[Callable] = None
        self.on_recovery_detected: Optional[Callable] = None
        self.on_health_change: Optional[Callable] = None
        
        # Performance tracking
        self._detection_times: List[float] = []
        
        logger.info(f"HealthMonitor initialized with {check_interval}s check interval")
    
    async def start(self):
        """Start health monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor started")
    
    async def stop(self):
        """Stop health monitoring"""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor stopped")
    
    async def get_current_metrics(self) -> HealthMetrics:
        """Get current system health metrics"""
        agents = list(self.agent_pool.agents.values())
        
        # Count agent states
        healthy = sum(1 for a in agents if a.state == AgentState.HEALTHY)
        degraded = sum(1 for a in agents if a.state == AgentState.DEGRADED)
        failed = sum(1 for a in agents if a.state in [
            AgentState.FAILED, AgentState.TIMEOUT, AgentState.TERMINATED
        ])
        
        # Calculate queue sizes and response times
        queue_sizes = []
        response_times = []
        total_tasks = 0
        failed_tasks = 0
        
        for agent in agents:
            status = await agent.get_health_status()
            queue_sizes.append(status["queue_size"])
            
            # Estimate response time from processing
            if agent.last_task_time:
                response_times.append(time.time() - agent.last_task_time)
            
            total_tasks += agent.tasks_processed + agent.tasks_failed
            failed_tasks += agent.tasks_failed
        
        # Calculate averages
        avg_queue = statistics.mean(queue_sizes) if queue_sizes else 0
        avg_response = statistics.mean(response_times) if response_times else 0
        error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
        
        return HealthMetrics(
            timestamp=datetime.utcnow(),
            total_agents=len(agents),
            healthy_agents=healthy,
            degraded_agents=degraded,
            failed_agents=failed,
            average_queue_size=avg_queue,
            average_response_time=avg_response,
            error_rate=error_rate
        )
    
    async def get_failure_detection_stats(self) -> Dict[str, Any]:
        """Get failure detection performance statistics"""
        if not self._detection_times:
            return {
                "average_detection_time": 0,
                "min_detection_time": 0,
                "max_detection_time": 0,
                "p95_detection_time": 0,
                "meets_threshold": True
            }
        
        avg_time = statistics.mean(self._detection_times)
        min_time = min(self._detection_times)
        max_time = max(self._detection_times)
        
        # Calculate 95th percentile
        sorted_times = sorted(self._detection_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_time
        
        return {
            "average_detection_time": avg_time,
            "min_detection_time": min_time,
            "max_detection_time": max_time,
            "p95_detection_time": p95_time,
            "meets_threshold": avg_time <= self.failure_threshold,
            "total_failures_detected": len(self.failure_events)
        }
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("HealthMonitor loop started")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Check all agents
                await self._check_agents()
                
                # Collect metrics
                metrics = await self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Trim history
                if len(self.metrics_history) > self.history_window:
                    self.metrics_history = self.metrics_history[-self.history_window:]
                
                # Check for health status changes
                await self._check_health_change(metrics)
                
                # Sleep for remaining interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.check_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_agents(self):
        """Check individual agent health"""
        current_time = time.time()
        failed_agents = []
        recovered_agents = []
        
        for agent_id, agent in self.agent_pool.agents.items():
            old_state = self._agent_states.get(agent_id)
            new_state = agent.state
            
            # Track state changes
            self._agent_states[agent_id] = new_state
            
            # Check for failures
            if new_state in [AgentState.FAILED, AgentState.TIMEOUT]:
                if old_state not in [AgentState.FAILED, AgentState.TIMEOUT]:
                    # New failure detected
                    failure_start = self._agent_failure_start.get(agent_id)
                    if not failure_start:
                        self._agent_failure_start[agent_id] = current_time
                        failure_start = current_time
                    
                    # Check if we've passed the detection window
                    detection_time = current_time - failure_start
                    if agent_id not in [f.agent_id for f in failed_agents]:
                        failed_agents.append((agent_id, new_state, detection_time))
                        logger.info(f"MONITOR: Agent {agent_id} failure detected in {detection_time:.4f}s")
            
            # Check for recoveries
            elif old_state in [AgentState.FAILED, AgentState.TIMEOUT] and new_state == AgentState.HEALTHY:
                recovered_agents.append(agent_id)
                if agent_id in self._agent_failure_start:
                    del self._agent_failure_start[agent_id]
                logger.info(f"MONITOR: Agent {agent_id} recovered")
            
            # Update heartbeat
            if new_state == AgentState.HEALTHY:
                self._agent_last_heartbeat[agent_id] = current_time
        
        # Process failures
        for agent_id, state, detection_time in failed_agents:
            await self._handle_failure(agent_id, state, detection_time)
        
        # Process recoveries
        for agent_id in recovered_agents:
            await self._handle_recovery(agent_id)
    
    async def _handle_failure(self, agent_id: str, state: AgentState, detection_time: float):
        """Handle detected failure"""
        # Record failure event
        event = FailureEvent(
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            failure_type=state.value,
            detection_time=detection_time,
            details={
                "state": state.value,
                "threshold": self.failure_threshold,
                "exceeded": detection_time > self.failure_threshold
            }
        )
        
        self.failure_events.append(event)
        self._detection_times.append(detection_time)
        
        # Trigger callback
        if self.on_failure_detected:
            try:
                await self.on_failure_detected(agent_id, event)
            except Exception as e:
                logger.error(f"Failure callback error: {e}")
        
        # Log detection performance
        if detection_time > self.failure_threshold:
            logger.warning(
                f"MONITOR: Failure detection for {agent_id} exceeded threshold: "
                f"{detection_time:.4f}s > {self.failure_threshold}s"
            )
    
    async def _handle_recovery(self, agent_id: str):
        """Handle detected recovery"""
        if self.on_recovery_detected:
            try:
                await self.on_recovery_detected(agent_id)
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")
    
    async def _check_health_change(self, metrics: HealthMetrics):
        """Check for overall health status changes"""
        if len(self.metrics_history) < 2:
            return
        
        prev_metrics = self.metrics_history[-2]
        
        if metrics.status != prev_metrics.status:
            logger.info(
                f"MONITOR: System health changed: "
                f"{prev_metrics.status.value} -> {metrics.status.value}"
            )
            
            if self.on_health_change:
                try:
                    await self.on_health_change(prev_metrics.status, metrics.status, metrics)
                except Exception as e:
                    logger.error(f"Health change callback error: {e}")