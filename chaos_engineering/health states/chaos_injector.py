"""
chaos_injector.py - Chaos Injection Mechanisms

Implements various failure injection strategies for chaos testing.
"""

import asyncio
import random
import logging
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import resource

from agent import Agent, AgentState, AgentPool

logger = logging.getLogger(__name__)


class ChaosType(Enum):
    """Types of chaos that can be injected"""
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_CRASH = "agent_crash"
    NETWORK_PARTITION = "network_partition"
    PACKET_LOSS = "packet_loss"
    LATENCY_SPIKE = "latency_spike"
    MEMORY_LEAK = "memory_leak"
    CPU_THROTTLE = "cpu_throttle"
    CASCADE_FAILURE = "cascade_failure"
    SLOW_DEATH = "slow_death"


@dataclass
class ChaosEvent:
    """Record of a chaos injection event"""
    event_id: str
    chaos_type: ChaosType
    target_agents: List[str]
    parameters: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    impact: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.end_time:
            return self.end_time - self.start_time
        return None


class ChaosInjector:
    """
    Orchestrates chaos injection into the agent system.
    """
    
    def __init__(self, agent_pool: AgentPool):
        self.agent_pool = agent_pool
        self.active_chaos: Dict[str, ChaosEvent] = {}
        self._chaos_counter = 0
        self._shutdown = False
        self._chaos_tasks: List[asyncio.Task] = []
        
        # Chaos configuration
        self.config = {
            "network": {
                "packet_loss_rate": 0.4,  # 40%
                "latency_ms": 500,
                "jitter_ms": 100
            },
            "agents": {
                "failure_count": 2,
                "failure_type": "timeout",
                "recovery_delay": 2.0
            },
            "resources": {
                "memory_leak_mb": 100,
                "cpu_throttle_percent": 80
            }
        }
        
        logger.info("ChaosInjector initialized")
    
    async def inject_chaos(
        self, 
        chaos_type: ChaosType,
        duration_seconds: float = 60.0,
        target_agents: Optional[List[str]] = None,
        **kwargs
    ) -> ChaosEvent:
        """
        Inject chaos of specified type.
        
        Args:
            chaos_type: Type of chaos to inject
            duration_seconds: How long to maintain the chaos
            target_agents: Specific agents to target (None = random selection)
            **kwargs: Additional parameters for specific chaos types
        """
        self._chaos_counter += 1
        event_id = f"chaos_{self._chaos_counter}"
        
        # Select target agents if not specified
        if not target_agents:
            agents = list(self.agent_pool.agents.values())
            num_targets = kwargs.get("num_targets", self.config["agents"]["failure_count"])
            target_agents = [a.id for a in random.sample(agents, min(num_targets, len(agents)))]
        
        # Create chaos event
        event = ChaosEvent(
            event_id=event_id,
            chaos_type=chaos_type,
            target_agents=target_agents,
            parameters=kwargs,
            start_time=datetime.utcnow()
        )
        
        self.active_chaos[event_id] = event
        logger.info(f"CHAOS: Initiating {chaos_type.value} on agents {target_agents}")
        
        # Start chaos based on type
        if chaos_type == ChaosType.AGENT_TIMEOUT:
            task = asyncio.create_task(self._inject_agent_timeout(event, duration_seconds))
        elif chaos_type == ChaosType.AGENT_CRASH:
            task = asyncio.create_task(self._inject_agent_crash(event, duration_seconds))
        elif chaos_type == ChaosType.NETWORK_PARTITION:
            task = asyncio.create_task(self._inject_network_partition(event, duration_seconds))
        elif chaos_type == ChaosType.PACKET_LOSS:
            task = asyncio.create_task(self._inject_packet_loss(event, duration_seconds))
        elif chaos_type == ChaosType.LATENCY_SPIKE:
            task = asyncio.create_task(self._inject_latency_spike(event, duration_seconds))
        elif chaos_type == ChaosType.CASCADE_FAILURE:
            task = asyncio.create_task(self._inject_cascade_failure(event, duration_seconds))
        elif chaos_type == ChaosType.SLOW_DEATH:
            task = asyncio.create_task(self._inject_slow_death(event, duration_seconds))
        else:
            raise ValueError(f"Unknown chaos type: {chaos_type}")
        
        self._chaos_tasks.append(task)
        return event
    
    async def stop_chaos(self, event_id: Optional[str] = None):
        """Stop specific or all chaos events"""
        if event_id:
            if event_id in self.active_chaos:
                event = self.active_chaos[event_id]
                event.end_time = datetime.utcnow()
                logger.info(f"CHAOS: Stopping {event_id}")
        else:
            # Stop all chaos
            self._shutdown = True
            for event in self.active_chaos.values():
                if not event.end_time:
                    event.end_time = datetime.utcnow()
            
            # Cancel all tasks
            for task in self._chaos_tasks:
                task.cancel()
            
            logger.info("CHAOS: All chaos events stopped")
    
    async def get_active_chaos(self) -> List[ChaosEvent]:
        """Get list of active chaos events"""
        return [
            event for event in self.active_chaos.values()
            if not event.end_time
        ]
    
    # Chaos injection implementations
    
    async def _inject_agent_timeout(self, event: ChaosEvent, duration: float):
        """Force agents into timeout state"""
        affected_agents = []
        
        try:
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_timeout()
                    affected_agents.append(agent_id)
                    logger.info(f"CHAOS: Forcing TIMEOUT state for Agent {agent_id}")
            
            event.impact["affected_agents"] = affected_agents
            
            # Maintain timeout for duration
            await asyncio.sleep(duration)
            
        except asyncio.CancelledError:
            pass
        finally:
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Agent timeout injection completed")
    
    async def _inject_agent_crash(self, event: ChaosEvent, duration: float):
        """Simulate agent crashes"""
        crashed_agents = []
        
        try:
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_failure()
                    crashed_agents.append(agent_id)
                    logger.info(f"CHAOS: Crashing Agent {agent_id}")
            
            event.impact["crashed_agents"] = crashed_agents
            
            # Keep agents crashed for duration
            await asyncio.sleep(duration)
            
        except asyncio.CancelledError:
            pass
        finally:
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Agent crash injection completed")
    
    async def _inject_network_partition(self, event: ChaosEvent, duration: float):
        """Simulate network partition between agents"""
        partition_groups = event.parameters.get("partition_groups", 2)
        agents = list(self.agent_pool.agents.values())
        
        # Divide agents into partition groups
        random.shuffle(agents)
        group_size = len(agents) // partition_groups
        groups = []
        
        for i in range(partition_groups):
            start_idx = i * group_size
            end_idx = start_idx + group_size if i < partition_groups - 1 else len(agents)
            groups.append(agents[start_idx:end_idx])
        
        logger.info(f"CHAOS: Creating {partition_groups} network partitions")
        
        try:
            # Apply packet loss between groups
            for i, group in enumerate(groups):
                for agent in group:
                    # 100% packet loss to agents in other groups
                    agent.inject_packet_loss(1.0)
            
            event.impact["partition_groups"] = [[a.id for a in g] for g in groups]
            
            await asyncio.sleep(duration)
            
        except asyncio.CancelledError:
            pass
        finally:
            # Restore network
            for agent in agents:
                agent.inject_packet_loss(0.0)
            
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Network partition healed")
    
    async def _inject_packet_loss(self, event: ChaosEvent, duration: float):
        """Inject packet loss"""
        loss_rate = event.parameters.get("loss_rate", self.config["network"]["packet_loss_rate"])
        
        try:
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_packet_loss(loss_rate)
                    logger.info(f"CHAOS: Injecting {loss_rate*100:.0f}% packet loss on Agent {agent_id}")
            
            event.impact["packet_loss_rate"] = loss_rate
            
            await asyncio.sleep(duration)
            
        except asyncio.CancelledError:
            pass
        finally:
            # Restore network
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_packet_loss(0.0)
            
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Packet loss injection completed")
    
    async def _inject_latency_spike(self, event: ChaosEvent, duration: float):
        """Inject latency spikes"""
        base_latency = event.parameters.get("latency_ms", self.config["network"]["latency_ms"])
        jitter = event.parameters.get("jitter_ms", self.config["network"]["jitter_ms"])
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < duration:
                for agent_id in event.target_agents:
                    agent = await self.agent_pool.get_agent(agent_id)
                    if agent:
                        # Add random jitter to latency
                        latency = base_latency + random.uniform(-jitter, jitter)
                        agent.inject_latency(max(0, latency))
                
                # Update latency periodically
                await asyncio.sleep(1.0)
            
            event.impact["avg_latency_ms"] = base_latency
            
        except asyncio.CancelledError:
            pass
        finally:
            # Remove latency
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_latency(0)
            
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Latency spike injection completed")
    
    async def _inject_cascade_failure(self, event: ChaosEvent, duration: float):
        """Simulate cascading failures"""
        initial_failures = event.parameters.get("initial_failures", 1)
        cascade_probability = event.parameters.get("cascade_probability", 0.5)
        cascade_delay = event.parameters.get("cascade_delay", 2.0)
        
        failed_agents = set()
        agents = list(self.agent_pool.agents.values())
        
        try:
            # Initial failures
            initial_targets = random.sample(agents, min(initial_failures, len(agents)))
            for agent in initial_targets:
                agent.inject_timeout()
                failed_agents.add(agent.id)
                logger.info(f"CHAOS: Initial cascade failure on Agent {agent.id}")
            
            event.impact["initial_failures"] = [a.id for a in initial_targets]
            cascaded_agents = []
            
            # Cascade to neighboring agents
            cascade_rounds = 0
            while cascade_rounds < 3:  # Limit cascade depth
                await asyncio.sleep(cascade_delay)
                
                # Find healthy agents that might cascade
                healthy_agents = [
                    a for a in agents 
                    if a.id not in failed_agents and a.state == AgentState.HEALTHY
                ]
                
                if not healthy_agents:
                    break
                
                # Cascade failures based on probability
                new_failures = []
                for agent in healthy_agents:
                    if random.random() < cascade_probability:
                        agent.inject_timeout()
                        failed_agents.add(agent.id)
                        new_failures.append(agent.id)
                        cascaded_agents.append(agent.id)
                        logger.info(f"CHAOS: Cascade failure spread to Agent {agent.id}")
                
                if not new_failures:
                    break
                
                cascade_rounds += 1
                # Reduce probability for next round
                cascade_probability *= 0.7
            
            event.impact["cascaded_agents"] = cascaded_agents
            event.impact["total_failed"] = len(failed_agents)
            
            # Maintain failure state
            remaining_time = duration - (cascade_rounds * cascade_delay)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
            
        except asyncio.CancelledError:
            pass
        finally:
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Cascade failure completed, {len(failed_agents)} agents affected")
    
    async def _inject_slow_death(self, event: ChaosEvent, duration: float):
        """Simulate gradual degradation leading to failure"""
        degradation_rate = event.parameters.get("degradation_rate", 0.1)
        
        try:
            # Track degradation state
            agent_health = {agent_id: 1.0 for agent_id in event.target_agents}
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < duration:
                for agent_id in event.target_agents:
                    agent = await self.agent_pool.get_agent(agent_id)
                    if agent and agent_health[agent_id] > 0:
                        # Gradually increase latency and failure rate
                        health = agent_health[agent_id]
                        
                        # Inject progressively worse latency
                        latency = (1 - health) * 1000  # Up to 1 second
                        agent.inject_latency(latency)
                        
                        # Increase packet loss
                        packet_loss = (1 - health) * 0.5  # Up to 50%
                        agent.inject_packet_loss(packet_loss)
                        
                        # Degrade health
                        agent_health[agent_id] = max(0, health - degradation_rate)
                        
                        # Force failure when health reaches zero
                        if agent_health[agent_id] == 0:
                            agent.inject_failure()
                            logger.info(f"CHAOS: Agent {agent_id} died from slow degradation")
                
                await asyncio.sleep(1.0)
            
            event.impact["final_health"] = agent_health
            event.impact["deaths"] = [aid for aid, h in agent_health.items() if h == 0]
            
        except asyncio.CancelledError:
            pass
        finally:
            # Reset all affected agents
            for agent_id in event.target_agents:
                agent = await self.agent_pool.get_agent(agent_id)
                if agent:
                    agent.inject_latency(0)
                    agent.inject_packet_loss(0)
            
            event.end_time = datetime.utcnow()
            logger.info(f"CHAOS: Slow death injection completed")


class ResourceChaos:
    """
    Inject resource-based chaos (memory, CPU, disk).
    """
    
    def __init__(self):
        self.memory_hogs = []
        self.cpu_burners = []
        self._original_cpu_affinity = None
        logger.info("ResourceChaos initialized")
    
    async def inject_memory_pressure(self, target_mb: int, duration: float):
        """Simulate memory pressure"""
        logger.info(f"CHAOS: Injecting {target_mb}MB memory pressure")
        
        try:
            # Allocate memory in chunks
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            chunks_needed = (target_mb * 1024 * 1024) // chunk_size
            
            for _ in range(chunks_needed):
                # Allocate and fill memory to prevent optimization
                chunk = bytearray(chunk_size)
                for i in range(0, chunk_size, 4096):
                    chunk[i] = 1
                self.memory_hogs.append(chunk)
            
            logger.info(f"CHAOS: Allocated {len(self.memory_hogs) * 10}MB")
            await asyncio.sleep(duration)
            
        except MemoryError:
            logger.error("CHAOS: Memory allocation failed - system limit reached")
        finally:
            # Release memory
            self.memory_hogs.clear()
            logger.info("CHAOS: Memory pressure released")
    
    async def inject_cpu_throttle(self, cpu_percent: int, duration: float):
        """Throttle CPU availability"""
        logger.info(f"CHAOS: Throttling CPU to {cpu_percent}%")
        
        try:
            # Get current process
            process = psutil.Process()
            
            # Save original CPU affinity
            try:
                self._original_cpu_affinity = process.cpu_affinity()
            except:
                self._original_cpu_affinity = None
            
            # Reduce CPU cores available
            cpu_count = psutil.cpu_count()
            target_cpus = max(1, int(cpu_count * cpu_percent / 100))
            
            try:
                # Set CPU affinity to limit cores
                if self._original_cpu_affinity:
                    process.cpu_affinity(list(range(target_cpus)))
                    logger.info(f"CHAOS: Limited to {target_cpus} CPU cores")
            except:
                logger.warning("CHAOS: CPU affinity not supported on this platform")
            
            # Also use CPU burner threads for additional pressure
            num_burners = cpu_count - target_cpus
            for _ in range(num_burners):
                task = asyncio.create_task(self._cpu_burner())
                self.cpu_burners.append(task)
            
            await asyncio.sleep(duration)
            
        finally:
            # Stop CPU burners
            for task in self.cpu_burners:
                task.cancel()
            self.cpu_burners.clear()
            
            # Restore CPU affinity
            if self._original_cpu_affinity:
                try:
                    process = psutil.Process()
                    process.cpu_affinity(self._original_cpu_affinity)
                except:
                    pass
            
            logger.info("CHAOS: CPU throttle removed")
    
    async def _cpu_burner(self):
        """Burn CPU cycles"""
        while True:
            # Perform intensive calculation
            _ = sum(i * i for i in range(10000))
            await asyncio.sleep(0)  # Yield to allow cancellation