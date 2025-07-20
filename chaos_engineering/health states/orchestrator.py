"""
orchestrator.py - Recovery Orchestration

Coordinates agent recovery, task redistribution, and system resilience.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import random

from agent import Agent, AgentState, AgentPool, Task
from monitor import HealthMonitor, FailureEvent

logger = logging.getLogger(__name__)


@dataclass
class RecoveryEvent:
    """Record of a recovery action"""
    timestamp: datetime
    failed_agent_id: str
    replacement_agent_id: str
    recovery_time: float
    tasks_recovered: int
    success: bool
    details: Dict[str, any] = field(default_factory=dict)


class RecoveryStrategy:
    """Base class for recovery strategies"""
    
    async def recover(self, failed_agent: Agent, agent_pool: AgentPool) -> Optional[Agent]:
        """Implement recovery logic"""
        raise NotImplementedError


class ReplaceStrategy(RecoveryStrategy):
    """Replace failed agent with a new instance"""
    
    async def recover(self, failed_agent: Agent, agent_pool: AgentPool) -> Optional[Agent]:
        """Replace the failed agent"""
        new_id = f"R{failed_agent.id}"  # Prefix with R for "Recovered"
        
        try:
            new_agent = await agent_pool.replace_agent(failed_agent.id, new_id)
            logger.info(f"RECOVERY: Agent {failed_agent.id} replaced with {new_id}")
            return new_agent
        except Exception as e:
            logger.error(f"RECOVERY: Failed to replace agent {failed_agent.id}: {e}")
            return None


class RedundancyStrategy(RecoveryStrategy):
    """Use redundant agents for recovery"""
    
    def __init__(self, redundancy_factor: int = 2):
        self.redundancy_factor = redundancy_factor
    
    async def recover(self, failed_agent: Agent, agent_pool: AgentPool) -> Optional[Agent]:
        """Activate redundant agent"""
        # In a real system, this would activate a standby agent
        # For demo, we'll create a new one
        new_id = f"S{failed_agent.id}"  # S for "Standby"
        
        try:
            new_agent = await agent_pool.replace_agent(failed_agent.id, new_id)
            logger.info(f"RECOVERY: Standby agent {new_id} activated for {failed_agent.id}")
            return new_agent
        except Exception as e:
            logger.error(f"RECOVERY: Failed to activate standby: {e}")
            return None


class RecoveryOrchestrator:
    """
    Orchestrates system recovery from failures.
    """
    
    def __init__(
        self,
        agent_pool: AgentPool,
        monitor: HealthMonitor,
        strategy: RecoveryStrategy = None,
        max_recovery_time: float = 2.0,  # 2 second target
        task_redistribution: bool = True
    ):
        self.agent_pool = agent_pool
        self.monitor = monitor
        self.strategy = strategy or ReplaceStrategy()
        self.max_recovery_time = max_recovery_time
        self.task_redistribution = task_redistribution
        
        # Recovery state
        self.recovery_events: List[RecoveryEvent] = []
        self.recovering_agents: Set[str] = set()
        self._recovery_lock = asyncio.Lock()
        
        # Task recovery
        self.orphaned_tasks: asyncio.Queue = asyncio.Queue()
        self._task_recovery_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self.total_recoveries = 0
        self.successful_recoveries = 0
        self.total_tasks_recovered = 0
        self.total_tasks_lost = 0
        
        # Setup callbacks
        monitor.on_failure_detected = self._handle_failure
        
        logger.info("RecoveryOrchestrator initialized")
    
    async def start(self):
        """Start recovery orchestration"""
        self._task_recovery_task = asyncio.create_task(self._task_recovery_loop())
        logger.info("RecoveryOrchestrator started")
    
    async def stop(self):
        """Stop recovery orchestration"""
        if self._task_recovery_task:
            self._task_recovery_task.cancel()
            try:
                await self._task_recovery_task
            except asyncio.CancelledError:
                pass
        logger.info("RecoveryOrchestrator stopped")
    
    async def get_recovery_stats(self) -> Dict[str, any]:
        """Get recovery performance statistics"""
        recovery_times = [e.recovery_time for e in self.recovery_events if e.success]
        
        if not recovery_times:
            return {
                "total_recoveries": self.total_recoveries,
                "successful_recoveries": self.successful_recoveries,
                "success_rate": 0,
                "average_recovery_time": 0,
                "max_recovery_time": 0,
                "meets_threshold": True,
                "tasks_recovered": self.total_tasks_recovered,
                "tasks_lost": self.total_tasks_lost
            }
        
        import statistics
        avg_time = statistics.mean(recovery_times)
        max_time = max(recovery_times)
        
        return {
            "total_recoveries": self.total_recoveries,
            "successful_recoveries": self.successful_recoveries,
            "success_rate": self.successful_recoveries / self.total_recoveries,
            "average_recovery_time": avg_time,
            "max_recovery_time": max_time,
            "meets_threshold": avg_time <= self.max_recovery_time,
            "tasks_recovered": self.total_tasks_recovered,
            "tasks_lost": self.total_tasks_lost,
            "data_integrity": self.total_tasks_recovered / (self.total_tasks_recovered + self.total_tasks_lost)
            if (self.total_tasks_recovered + self.total_tasks_lost) > 0 else 1.0
        }
    
    async def _handle_failure(self, agent_id: str, failure_event: FailureEvent):
        """Handle agent failure and initiate recovery"""
        logger.info(f"RECOVERY: Initiating recovery for agent {agent_id}")
        
        async with self._recovery_lock:
            if agent_id in self.recovering_agents:
                logger.warning(f"RECOVERY: Agent {agent_id} already recovering")
                return
            
            self.recovering_agents.add(agent_id)
        
        recovery_start = time.time()
        self.total_recoveries += 1
        
        try:
            # Get the failed agent
            failed_agent = await self.agent_pool.get_agent(agent_id)
            if not failed_agent:
                logger.error(f"RECOVERY: Failed agent {agent_id} not found")
                return
            
            # Save orphaned tasks
            tasks_saved = await self._save_orphaned_tasks(failed_agent)
            
            # Execute recovery strategy
            new_agent = await self.strategy.recover(failed_agent, self.agent_pool)
            
            recovery_time = time.time() - recovery_start
            success = new_agent is not None
            
            if success:
                self.successful_recoveries += 1
                logger.info(f"RECOVERY: Agent {agent_id} recovered as {new_agent.id} in {recovery_time:.3f}s")
                
                # Redistribute saved tasks
                if self.task_redistribution:
                    await self._redistribute_tasks(new_agent, tasks_saved)
            else:
                logger.error(f"RECOVERY: Failed to recover agent {agent_id}")
            
            # Record recovery event
            event = RecoveryEvent(
                timestamp=datetime.utcnow(),
                failed_agent_id=agent_id,
                replacement_agent_id=new_agent.id if new_agent else "NONE",
                recovery_time=recovery_time,
                tasks_recovered=tasks_saved,
                success=success,
                details={
                    "strategy": self.strategy.__class__.__name__,
                    "threshold_met": recovery_time <= self.max_recovery_time
                }
            )
            
            self.recovery_events.append(event)
            
            # Check recovery time threshold
            if recovery_time > self.max_recovery_time:
                logger.warning(
                    f"RECOVERY: Recovery time exceeded threshold: "
                    f"{recovery_time:.3f}s > {self.max_recovery_time}s"
                )
            
        except Exception as e:
            logger.error(f"RECOVERY: Unexpected error recovering {agent_id}: {e}")
        finally:
            self.recovering_agents.discard(agent_id)
    
    async def _save_orphaned_tasks(self, failed_agent: Agent) -> int:
        """Save tasks from failed agent"""
        tasks_saved = 0
        
        try:
            # Save current task
            if failed_agent.current_task:
                await self.orphaned_tasks.put(failed_agent.current_task)
                tasks_saved += 1
                logger.debug(f"RECOVERY: Saved current task {failed_agent.current_task.id}")
            
            # Save queued tasks
            while not failed_agent.task_queue.empty():
                try:
                    task = failed_agent.task_queue.get_nowait()
                    await self.orphaned_tasks.put(task)
                    tasks_saved += 1
                    logger.debug(f"RECOVERY: Saved queued task {task.id}")
                except asyncio.QueueEmpty:
                    break
            
            logger.info(f"RECOVERY: Saved {tasks_saved} tasks from agent {failed_agent.id}")
            
        except Exception as e:
            logger.error(f"RECOVERY: Error saving tasks: {e}")
        
        return tasks_saved
    
    async def _redistribute_tasks(self, new_agent: Agent, task_count: int):
        """Redistribute tasks to recovered agent"""
        redistributed = 0
        
        try:
            # Give priority to the new agent for its own tasks
            for _ in range(task_count):
                if not self.orphaned_tasks.empty():
                    try:
                        task = self.orphaned_tasks.get_nowait()
                        success = await new_agent.submit_task(task)
                        if success:
                            redistributed += 1
                            self.total_tasks_recovered += 1
                        else:
                            # Put back for general redistribution
                            await self.orphaned_tasks.put(task)
                    except asyncio.QueueEmpty:
                        break
            
            logger.info(f"RECOVERY: Redistributed {redistributed} tasks to {new_agent.id}")
            
        except Exception as e:
            logger.error(f"RECOVERY: Error redistributing tasks: {e}")
    
    async def _task_recovery_loop(self):
        """Background loop to recover orphaned tasks"""
        while True:
            try:
                # Wait for orphaned task with timeout
                task = await asyncio.wait_for(self.orphaned_tasks.get(), timeout=1.0)
                
                # Find healthy agent with lowest queue
                healthy_agents = await self.agent_pool.get_healthy_agents()
                if not healthy_agents:
                    # No healthy agents, put task back
                    await self.orphaned_tasks.put(task)
                    await asyncio.sleep(0.5)
                    continue
                
                # Sort by queue size
                agent_loads = []
                for agent in healthy_agents:
                    status = await agent.get_health_status()
                    agent_loads.append((agent, status["queue_size"]))
                
                agent_loads.sort(key=lambda x: x[1])
                
                # Try to assign to least loaded agent
                assigned = False
                for agent, _ in agent_loads[:3]:  # Try top 3 least loaded
                    if await agent.submit_task(task):
                        logger.debug(f"RECOVERY: Orphaned task {task.id} assigned to {agent.id}")
                        self.total_tasks_recovered += 1
                        assigned = True
                        break
                
                if not assigned:
                    # Put back in queue
                    await self.orphaned_tasks.put(task)
                    self.total_tasks_lost += 1
                    logger.warning(f"RECOVERY: Failed to assign orphaned task {task.id}")
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"RECOVERY: Task recovery loop error: {e}")
                await asyncio.sleep(1.0)