"""
agent.py - Resilient Agent Implementation

Production-ready agent with health states, failure detection, and recovery capabilities.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import random

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent health states"""
    INITIALIZING = "INITIALIZING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    TERMINATED = "TERMINATED"


@dataclass
class Task:
    """Task representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.name:
            self.name = f"Task-{self.id}"


class Agent:
    """
    Resilient agent with health monitoring and graceful degradation.
    """
    
    def __init__(
        self, 
        agent_id: str,
        health_check_interval: float = 1.0,
        task_timeout: float = 5.0,
        failure_threshold: int = 3,
        recovery_delay: float = 2.0
    ):
        self.id = agent_id
        self.state = AgentState.INITIALIZING
        self.health_check_interval = health_check_interval
        self.task_timeout = task_timeout
        self.failure_threshold = failure_threshold
        self.recovery_delay = recovery_delay
        
        # Metrics
        self.tasks_processed = 0
        self.tasks_failed = 0
        self.consecutive_failures = 0
        self.last_heartbeat = time.time()
        self.last_task_time = None
        self.startup_time = time.time()
        
        # Task queue and processing
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.current_task: Optional[Task] = None
        self.processing_lock = asyncio.Lock()
        
        # Health monitoring
        self._health_task: Optional[asyncio.Task] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_failure: Optional[Callable] = None
        
        # Chaos injection hooks
        self._force_timeout = False
        self._force_failure = False
        self._injected_latency = 0.0
        self._packet_loss_rate = 0.0
        
        logger.info(f"Agent {self.id} initializing")
    
    async def start(self):
        """Start the agent"""
        try:
            # Initialize resources
            await self._initialize()
            
            # Start health monitoring
            self._health_task = asyncio.create_task(self._health_monitor())
            
            # Start task processing
            self._processing_task = asyncio.create_task(self._process_tasks())
            
            # Mark as healthy
            await self._change_state(AgentState.HEALTHY)
            logger.info(f"Agent {self.id} started successfully")
            
        except Exception as e:
            logger.error(f"Agent {self.id} failed to start: {e}")
            await self._change_state(AgentState.FAILED)
            raise
    
    async def stop(self):
        """Gracefully stop the agent"""
        logger.info(f"Agent {self.id} stopping")
        self._shutdown_event.set()
        
        # Cancel tasks
        if self._health_task:
            self._health_task.cancel()
        if self._processing_task:
            self._processing_task.cancel()
        
        # Wait for current task to complete
        async with self.processing_lock:
            if self.current_task:
                logger.info(f"Agent {self.id} waiting for current task to complete")
        
        await self._change_state(AgentState.TERMINATED)
        logger.info(f"Agent {self.id} stopped")
    
    async def submit_task(self, task: Task) -> bool:
        """Submit a task to the agent"""
        if self.state not in [AgentState.HEALTHY, AgentState.DEGRADED]:
            return False
        
        try:
            # Simulate packet loss
            if self._packet_loss_rate > 0 and random.random() < self._packet_loss_rate:
                logger.warning(f"Agent {self.id} dropped task {task.id} due to packet loss")
                return False
            
            await self.task_queue.put(task)
            logger.debug(f"Agent {self.id} queued task {task.id}")
            return True
            
        except Exception as e:
            logger.error(f"Agent {self.id} failed to queue task: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "id": self.id,
            "state": self.state.value,
            "uptime": time.time() - self.startup_time,
            "last_heartbeat": time.time() - self.last_heartbeat,
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "queue_size": self.task_queue.qsize(),
            "current_task": self.current_task.id if self.current_task else None,
            "consecutive_failures": self.consecutive_failures
        }
    
    # Chaos injection methods
    def inject_timeout(self):
        """Force agent into timeout state"""
        logger.warning(f"Agent {self.id} chaos: Injecting timeout")
        self._force_timeout = True
    
    def inject_failure(self):
        """Force agent failure"""
        logger.warning(f"Agent {self.id} chaos: Injecting failure")
        self._force_failure = True
    
    def inject_latency(self, latency_ms: float):
        """Add artificial latency to processing"""
        logger.warning(f"Agent {self.id} chaos: Injecting {latency_ms}ms latency")
        self._injected_latency = latency_ms / 1000.0
    
    def inject_packet_loss(self, loss_rate: float):
        """Simulate packet loss"""
        logger.warning(f"Agent {self.id} chaos: Injecting {loss_rate*100}% packet loss")
        self._packet_loss_rate = loss_rate
    
    # Private methods
    async def _initialize(self):
        """Initialize agent resources"""
        await asyncio.sleep(0.1)  # Simulate initialization
        logger.debug(f"Agent {self.id} initialized")
    
    async def _change_state(self, new_state: AgentState):
        """Change agent state with notification"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"Agent {self.id} state: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                try:
                    await self.on_state_change(self, old_state, new_state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")
    
    async def _health_monitor(self):
        """Monitor agent health"""
        while not self._shutdown_event.is_set():
            try:
                # Check for forced states
                if self._force_timeout:
                    await self._change_state(AgentState.TIMEOUT)
                    self._force_timeout = False
                    continue
                
                if self._force_failure:
                    await self._change_state(AgentState.FAILED)
                    self._force_failure = False
                    if self.on_failure:
                        await self.on_failure(self, "Forced failure")
                    continue
                
                # Update heartbeat
                self.last_heartbeat = time.time()
                
                # Check task processing health
                if self.state == AgentState.HEALTHY:
                    if self.consecutive_failures >= self.failure_threshold:
                        await self._change_state(AgentState.DEGRADED)
                
                # Attempt recovery from degraded state
                elif self.state == AgentState.DEGRADED:
                    if self.consecutive_failures == 0:
                        await self._change_state(AgentState.HEALTHY)
                
                # Recovery from timeout
                elif self.state == AgentState.TIMEOUT:
                    await asyncio.sleep(self.recovery_delay)
                    await self._change_state(AgentState.RECOVERING)
                    self.consecutive_failures = 0
                    await self._change_state(AgentState.HEALTHY)
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent {self.id} health monitor error: {e}")
    
    async def _process_tasks(self):
        """Process tasks from queue"""
        while not self._shutdown_event.is_set():
            try:
                # Wait for task with timeout
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                async with self.processing_lock:
                    self.current_task = task
                    
                    # Skip processing if not healthy
                    if self.state not in [AgentState.HEALTHY, AgentState.DEGRADED]:
                        logger.warning(f"Agent {self.id} skipping task {task.id} - not healthy")
                        await self.task_queue.put(task)  # Re-queue
                        continue
                    
                    # Process the task
                    success = await self._process_single_task(task)
                    
                    if success:
                        self.tasks_processed += 1
                        self.consecutive_failures = 0
                        if self.on_task_complete:
                            await self.on_task_complete(self, task)
                    else:
                        self.tasks_failed += 1
                        self.consecutive_failures += 1
                        task.retries += 1
                        
                        # Re-queue if under retry limit
                        if task.retries < task.max_retries:
                            await self.task_queue.put(task)
                    
                    self.current_task = None
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent {self.id} task processing error: {e}")
                self.consecutive_failures += 1
    
    async def _process_single_task(self, task: Task) -> bool:
        """Process a single task"""
        try:
            start_time = time.time()
            
            # Add injected latency
            if self._injected_latency > 0:
                await asyncio.sleep(self._injected_latency)
            
            # Simulate task processing
            processing_time = random.uniform(0.1, 0.5)
            
            # Check for timeout
            if self.state == AgentState.TIMEOUT:
                raise TimeoutError("Agent in timeout state")
            
            # Simulate processing with timeout
            await asyncio.wait_for(
                asyncio.sleep(processing_time),
                timeout=self.task_timeout
            )
            
            # Mark task complete
            task.processed_by = self.id
            task.completed_at = datetime.utcnow()
            
            elapsed = time.time() - start_time
            logger.debug(f"Agent {self.id} processed task {task.id} in {elapsed:.3f}s")
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Agent {self.id} task {task.id} timed out")
            return False
        except Exception as e:
            logger.error(f"Agent {self.id} failed to process task {task.id}: {e}")
            return False


class AgentPool:
    """Manages a pool of agents"""
    
    def __init__(self, size: int = 6):
        self.size = size
        self.agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the agent pool"""
        async with self._lock:
            for i in range(self.size):
                agent_id = chr(65 + i)  # A, B, C, etc.
                agent = Agent(agent_id)
                self.agents[agent_id] = agent
                await agent.start()
    
    async def get_healthy_agents(self) -> List[Agent]:
        """Get all healthy agents"""
        return [
            agent for agent in self.agents.values()
            if agent.state in [AgentState.HEALTHY, AgentState.DEGRADED]
        ]
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get specific agent"""
        return self.agents.get(agent_id)
    
    async def replace_agent(self, old_id: str, new_id: str) -> Optional[Agent]:
        """Replace a failed agent"""
        async with self._lock:
            # Stop old agent
            if old_id in self.agents:
                await self.agents[old_id].stop()
                del self.agents[old_id]
            
            # Create new agent
            new_agent = Agent(new_id)
            self.agents[new_id] = new_agent
            await new_agent.start()
            
            return new_agent
    
    async def shutdown(self):
        """Shutdown all agents"""
        async with self._lock:
            for agent in self.agents.values():
                await agent.stop()