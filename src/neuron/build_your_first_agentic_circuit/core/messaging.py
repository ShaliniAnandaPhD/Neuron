"""
Neuron Framework: SynapticBus Message Routing System 


Advanced message routing system that handles communication between agents
with priorities, load balancing, fault tolerance, and observability.
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import heapq
import threading
from concurrent.futures import ThreadPoolExecutor

from .base import Message, MessagePriority, MessageType, BaseAgent

logger = logging.getLogger(__name__)

# =====================================
# Routing Types and Configuration
# =====================================

class RoutingStrategy(Enum):
    """Message routing strategies"""
    DIRECT = "direct"  # Direct point-to-point
    BROADCAST = "broadcast"  # Send to all agents
    ROUND_ROBIN = "round_robin"  # Load balance between agents
    CAPABILITY_BASED = "capability_based"  # Route based on agent capabilities
    LOAD_BALANCED = "load_balanced"  # Route to least busy agent

@dataclass
class RoutingRule:
    """Defines how messages should be routed"""
    pattern: Dict[str, Any]  # Pattern to match against message
    strategy: RoutingStrategy
    target_agents: List[str] = field(default_factory=list)
    required_capabilities: Set[str] = field(default_factory=set)
    priority_boost: int = 0  # Boost message priority
    
    def matches(self, message: Message) -> bool:
        """Check if this rule matches a message"""
        for key, value in self.pattern.items():
            if key == 'type' and message.type.value != value:
                return False
            elif key == 'sender_pattern' and not message.sender_id.startswith(value):
                return False
            elif key == 'content_key' and value not in message.content:
                return False
            elif key in message.content and message.content[key] != value:
                return False
        return True

@dataclass
class MessageStats:
    """Statistics for message routing"""
    total_messages: int = 0
    successful_routes: int = 0
    failed_routes: int = 0
    average_latency: float = 0.0
    messages_by_priority: Dict[MessagePriority, int] = field(default_factory=lambda: defaultdict(int))
    messages_by_type: Dict[MessageType, int] = field(default_factory=lambda: defaultdict(int))
    
    def update_latency(self, latency: float):
        """Update average latency with new measurement"""
        if self.successful_routes == 0:
            self.average_latency = latency
        else:
            total_latency = self.average_latency * self.successful_routes
            self.average_latency = (total_latency + latency) / (self.successful_routes + 1)

# =====================================
# Priority Queue for Messages
# =====================================

class PriorityMessageQueue:
    """Thread-safe priority queue for messages"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue = []
        self._index = 0  # For maintaining insertion order for same priority
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
    
    def put(self, message: Message) -> bool:
        """Add message to queue"""
        with self._not_empty:
            if len(self._queue) >= self.max_size:
                # Remove lowest priority message
                if self._queue:
                    heapq.heappop(self._queue)
                else:
                    return False
            
            # Higher priority = lower number in heapq (min-heap)
            priority_value = -message.priority.value
            heapq.heappush(self._queue, (priority_value, self._index, message))
            self._index += 1
            self._not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get highest priority message"""
        with self._not_empty:
            if not self._queue:
                if timeout is None:
                    self._not_empty.wait()
                else:
                    self._not_empty.wait(timeout)
            
            if self._queue:
                _, _, message = heapq.heappop(self._queue)
                return message
            return None
    
    def size(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self._queue)
    
    def clear(self):
        """Clear the queue"""
        with self._lock:
            self._queue.clear()

# =====================================
# SynapticBus - Main Message Router
# =====================================

class SynapticBus:
    """
    Advanced message routing system for agent communication
    
    The SynapticBus handles all message routing between agents with features like:
    - Priority-based message queuing
    - Multiple routing strategies  
    - Load balancing and fault tolerance
    - Message persistence and replay
    - Comprehensive monitoring and metrics
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the SynapticBus"""
        self.config = config or {}
        
        # Agent registry
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_capabilities: Dict[str, Set[str]] = {}
        
        # Message routing
        self.message_queue = PriorityMessageQueue(
            max_size=self.config.get('max_queue_size', 10000)
        )
        self.routing_rules: List[RoutingRule] = []
        self.default_strategy = RoutingStrategy.DIRECT
        
        # Load balancing
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.agent_load: Dict[str, int] = defaultdict(int)  # Number of pending messages
        
        # Fault tolerance
        self.failed_agents: Set[str] = set()
        self.retry_counts: Dict[str, int] = defaultdict(int)
        self.max_retries = self.config.get('max_retries', 3)
        
        # Message persistence (for replay)
        self.message_history: deque = deque(
            maxlen=self.config.get('history_size', 1000)
        )
        
        # Monitoring
        self.stats = MessageStats()
        self.message_hooks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Threading
        self._running = False
        self._worker_threads: List[threading.Thread] = []
        self._lock = threading.RLock()
        
        logger.info("SynapticBus initialized")
    
    # =====================================
    # Agent Management
    # =====================================
    
    def register_agent(self, agent: BaseAgent) -> bool:
        """Register an agent with the bus"""
        with self._lock:
            if agent.agent_id in self.agents:
                logger.warning(f"Agent {agent.agent_id} already registered")
                return False
            
            self.agents[agent.agent_id] = agent
            self.agent_capabilities[agent.agent_id] = agent.capabilities.capabilities
            
            # Set the synaptic bus reference in the agent
            agent.synaptic_bus = self
            
            logger.info(f"Registered agent {agent.agent_id} with capabilities: {agent.capabilities.capabilities}")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        with self._lock:
            if agent_id not in self.agents:
                return False
            
            # Remove from all tracking
            del self.agents[agent_id]
            if agent_id in self.agent_capabilities:
                del self.agent_capabilities[agent_id]
            if agent_id in self.failed_agents:
                self.failed_agents.remove(agent_id)
            if agent_id in self.agent_load:
                del self.agent_load[agent_id]
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def get_healthy_agents(self) -> List[str]:
        """Get list of healthy agent IDs"""
        healthy = []
        for agent_id, agent in self.agents.items():
            if agent_id not in self.failed_agents and agent.is_healthy():
                healthy.append(agent_id)
        return healthy
    
    # =====================================
    # Routing Rules Management
    # =====================================
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a routing rule"""
        self.routing_rules.append(rule)
        logger.debug(f"Added routing rule: {rule.pattern} -> {rule.strategy.value}")
    
    def remove_routing_rule(self, rule: RoutingRule):
        """Remove a routing rule"""
        if rule in self.routing_rules:
            self.routing_rules.remove(rule)
    
    def clear_routing_rules(self):
        """Clear all routing rules"""
        self.routing_rules.clear()
    
    def find_matching_rule(self, message: Message) -> Optional[RoutingRule]:
        """Find the first routing rule that matches a message"""
        for rule in self.routing_rules:
            if rule.matches(message):
                return rule
        return None
    
    # =====================================
    # Message Routing
    # =====================================
    
    async def route_message(self, message: Message) -> bool:
        """Route a message to appropriate agent(s)"""
        start_time = time.time()
        
        try:
            # Update statistics
            self.stats.total_messages += 1
            self.stats.messages_by_priority[message.priority] += 1
            self.stats.messages_by_type[message.type] += 1
            
            # Store in history
            self.message_history.append({
                'message': message.to_dict(),
                'timestamp': start_time,
                'status': 'processing'
            })
            
            # Check for expired message
            if message.is_expired():
                logger.warning(f"Dropping expired message: {message.id}")
                return False
            
            # Find routing rule or use default strategy
            rule = self.find_matching_rule(message)
            strategy = rule.strategy if rule else self.default_strategy
            
            # Boost priority if rule specifies it
            if rule and rule.priority_boost > 0:
                original_priority = message.priority
                boosted_value = min(4, message.priority.value + rule.priority_boost)
                message.priority = MessagePriority(boosted_value)
                logger.debug(f"Boosted message priority: {original_priority.value} -> {message.priority.value}")
            
            # Route based on strategy
            success = await self._route_by_strategy(message, strategy, rule)
            
            # Update statistics
            if success:
                self.stats.successful_routes += 1
                latency = time.time() - start_time
                self.stats.update_latency(latency)
            else:
                self.stats.failed_routes += 1
            
            # Trigger hooks
            self._trigger_message_hook('message_routed', {
                'message': message,
                'strategy': strategy.value,
                'success': success,
                'latency': time.time() - start_time
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Message routing error: {e}")
            self.stats.failed_routes += 1
            return False
    
    async def _route_by_strategy(self, message: Message, strategy: RoutingStrategy, 
                               rule: Optional[RoutingRule] = None) -> bool:
        """Route message using specific strategy"""
        
        if strategy == RoutingStrategy.DIRECT:
            return await self._route_direct(message)
        
        elif strategy == RoutingStrategy.BROADCAST:
            return await self._route_broadcast(message)
        
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            target_agents = rule.target_agents if rule else list(self.get_healthy_agents())
            return await self._route_round_robin(message, target_agents)
        
        elif strategy == RoutingStrategy.CAPABILITY_BASED:
            required_caps = rule.required_capabilities if rule else set()
            return await self._route_by_capability(message, required_caps)
        
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            target_agents = rule.target_agents if rule else list(self.get_healthy_agents())
            return await self._route_load_balanced(message, target_agents)
        
        else:
            logger.error(f"Unknown routing strategy: {strategy}")
            return False
    
    async def _route_direct(self, message: Message) -> bool:
        """Route message directly to specified recipient"""
        if message.recipient_id == "*":
            return await self._route_broadcast(message)
        
        agent = self.agents.get(message.recipient_id)
        if not agent:
            logger.warning(f"Agent not found: {message.recipient_id}")
            return False
        
        if message.recipient_id in self.failed_agents:
            logger.warning(f"Agent failed: {message.recipient_id}")
            return False
        
        return await self._deliver_message(agent, message)
    
    async def _route_broadcast(self, message: Message) -> bool:
        """Broadcast message to all healthy agents except sender"""
        healthy_agents = self.get_healthy_agents()
        if message.sender_id in healthy_agents:
            healthy_agents.remove(message.sender_id)
        
        if not healthy_agents:
            logger.warning("No healthy agents for broadcast")
            return False
        
        # Send to all healthy agents
        results = []
        for agent_id in healthy_agents:
            agent = self.agents[agent_id]
            result = await self._deliver_message(agent, message)
            results.append(result)
        
        # Consider success if at least one delivery succeeded
        return any(results)
    
    async def _route_round_robin(self, message: Message, target_agents: List[str]) -> bool:
        """Route using round-robin load balancing"""
        healthy_targets = [aid for aid in target_agents if aid in self.get_healthy_agents()]
        
        if not healthy_targets:
            logger.warning("No healthy target agents for round-robin")
            return False
        
        # Get next agent in round-robin
        counter_key = ",".join(sorted(healthy_targets))
        index = self.round_robin_counters[counter_key] % len(healthy_targets)
        self.round_robin_counters[counter_key] += 1
        
        selected_agent_id = healthy_targets[index]
        agent = self.agents[selected_agent_id]
        
        return await self._deliver_message(agent, message)
    
    async def _route_by_capability(self, message: Message, required_capabilities: Set[str]) -> bool:
        """Route to agent with required capabilities"""
        if not required_capabilities:
            # No specific requirements, use direct routing
            return await self._route_direct(message)
        
        # Find agents with all required capabilities
        suitable_agents = []
        for agent_id in self.get_healthy_agents():
            agent_caps = self.agent_capabilities.get(agent_id, set())
            if required_capabilities.issubset(agent_caps):
                suitable_agents.append(agent_id)
        
        if not suitable_agents:
            logger.warning(f"No agents found with capabilities: {required_capabilities}")
            return False
        
        # Use least loaded agent
        selected_agent_id = min(suitable_agents, key=lambda aid: self.agent_load.get(aid, 0))
        agent = self.agents[selected_agent_id]
        
        return await self._deliver_message(agent, message)
    
    async def _route_load_balanced(self, message: Message, target_agents: List[str]) -> bool:
        """Route to least loaded agent"""
        healthy_targets = [aid for aid in target_agents if aid in self.get_healthy_agents()]
        
        if not healthy_targets:
            logger.warning("No healthy target agents for load balancing")
            return False
        
        # Select agent with lowest load
        selected_agent_id = min(healthy_targets, key=lambda aid: self.agent_load.get(aid, 0))
        agent = self.agents[selected_agent_id]
        
        return await self._deliver_message(agent, message)
    
    async def _deliver_message(self, agent: BaseAgent, message: Message) -> bool:
        """Deliver message to specific agent"""
        try:
            # Increment load counter
            self.agent_load[agent.agent_id] += 1
            
            # Attempt delivery
            success = await agent.receive_message(message)
            
            if success:
                # Reset retry count on success
                if agent.agent_id in self.retry_counts:
                    del self.retry_counts[agent.agent_id]
                
                logger.debug(f"Message {message.id} delivered to {agent.agent_id}")
            else:
                # Handle delivery failure
                await self._handle_delivery_failure(agent.agent_id, message)
            
            return success
            
        except Exception as e:
            logger.error(f"Message delivery error to {agent.agent_id}: {e}")
            await self._handle_delivery_failure(agent.agent_id, message)
            return False
        
        finally:
            # Decrement load counter
            if self.agent_load[agent.agent_id] > 0:
                self.agent_load[agent.agent_id] -= 1
    
    async def _handle_delivery_failure(self, agent_id: str, message: Message):
        """Handle failed message delivery"""
        self.retry_counts[agent_id] += 1
        
        if self.retry_counts[agent_id] >= self.max_retries:
            logger.error(f"Agent {agent_id} failed {self.max_retries} times, marking as failed")
            self.failed_agents.add(agent_id)
            
            # Trigger agent failure hook
            self._trigger_message_hook('agent_failed', {
                'agent_id': agent_id,
                'retry_count': self.retry_counts[agent_id],
                'message': message
            })
        else:
            logger.warning(f"Delivery failed to {agent_id}, retry {self.retry_counts[agent_id]}/{self.max_retries}")
    
    # =====================================
    # Message Queue Management
    # =====================================
    
    def queue_message(self, message: Message) -> bool:
        """Add message to processing queue"""
        return self.message_queue.put(message)
    
    def get_queued_message(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Get next message from queue"""
        return self.message_queue.get(timeout)
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.message_queue.size()
    
    def clear_queue(self):
        """Clear the message queue"""
        self.message_queue.clear()
    
    # =====================================
    # Health and Recovery
    # =====================================
    
    def mark_agent_healthy(self, agent_id: str):
        """Mark an agent as healthy (recovery)"""
        if agent_id in self.failed_agents:
            self.failed_agents.remove(agent_id)
            if agent_id in self.retry_counts:
                del self.retry_counts[agent_id]
            
            logger.info(f"Agent {agent_id} marked as healthy (recovered)")
            
            self._trigger_message_hook('agent_recovered', {
                'agent_id': agent_id,
                'timestamp': time.time()
            })
    
    def mark_agent_failed(self, agent_id: str):
        """Manually mark an agent as failed"""
        self.failed_agents.add(agent_id)
        logger.warning(f"Agent {agent_id} manually marked as failed")
    
    async def health_check_agents(self) -> Dict[str, bool]:
        """Perform health check on all agents"""
        results = {}
        
        for agent_id, agent in self.agents.items():
            try:
                # Send health check message
                health_message = Message(
                    type=MessageType.HEALTH_CHECK,
                    sender_id="synaptic_bus",
                    recipient_id=agent_id,
                    content={'check_type': 'ping'},
                    ttl=5.0  # 5 second timeout
                )
                
                # Try to deliver health check
                success = await self._deliver_message(agent, health_message)
                results[agent_id] = success and agent.is_healthy()
                
                if not results[agent_id] and agent_id not in self.failed_agents:
                    await self._handle_delivery_failure(agent_id, health_message)
                elif results[agent_id] and agent_id in self.failed_agents:
                    self.mark_agent_healthy(agent_id)
                    
            except Exception as e:
                logger.error(f"Health check failed for {agent_id}: {e}")
                results[agent_id] = False
        
        return results
    
    # =====================================
    # Lifecycle Management
    # =====================================
    
    def start(self, num_workers: int = 4):
        """Start the SynapticBus with worker threads"""
        if self._running:
            logger.warning("SynapticBus already running")
            return
        
        self._running = True
        
        # Start worker threads for message processing
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._message_worker,
                name=f"SynapticBus-Worker-{i}",
                daemon=True
            )
            worker.start()
            self._worker_threads.append(worker)
        
        logger.info(f"SynapticBus started with {num_workers} worker threads")
    
    def stop(self):
        """Stop the SynapticBus"""
        if not self._running:
            return
        
        self._running = False
        
        # Clear the queue to wake up workers
        self.clear_queue()
        
        # Wait for workers to finish
        for worker in self._worker_threads:
            worker.join(timeout=5.0)
        
        self._worker_threads.clear()
        logger.info("SynapticBus stopped")
    
    def _message_worker(self):
        """Worker thread for processing queued messages"""
        logger.debug(f"Message worker {threading.current_thread().name} started")
        
        while self._running:
            try:
                # Get message from queue with timeout
                message = self.get_queued_message(timeout=1.0)
                if message:
                    # Process message asynchronously
                    asyncio.run(self.route_message(message))
            except Exception as e:
                logger.error(f"Message worker error: {e}")
        
        logger.debug(f"Message worker {threading.current_thread().name} stopped")
    
    # =====================================
    # Monitoring and Hooks
    # =====================================
    
    def add_message_hook(self, event_name: str, callback: Callable):
        """Add a message processing hook"""
        self.message_hooks[event_name].append(callback)
    
    def remove_message_hook(self, event_name: str, callback: Callable):
        """Remove a message processing hook"""
        if callback in self.message_hooks[event_name]:
            self.message_hooks[event_name].remove(callback)
    
    def _trigger_message_hook(self, event_name: str, event_data: Dict[str, Any]):
        """Trigger message processing hooks"""
        for callback in self.message_hooks[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event_data))
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Message hook error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            'total_messages': self.stats.total_messages,
            'successful_routes': self.stats.successful_routes,
            'failed_routes': self.stats.failed_routes,
            'success_rate': (self.stats.successful_routes / max(1, self.stats.total_messages)) * 100,
            'average_latency': self.stats.average_latency,
            'queue_size': self.get_queue_size(),
            'registered_agents': len(self.agents),
            'healthy_agents': len(self.get_healthy_agents()),
            'failed_agents': len(self.failed_agents),
            'messages_by_priority': {p.value: count for p, count in self.stats.messages_by_priority.items()},
            'messages_by_type': {t.value: count for t, count in self.stats.messages_by_type.items()},
            'agent_load': dict(self.agent_load),
            'routing_rules': len(self.routing_rules)
        }
    
    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents"""
        status = {}
        for agent_id, agent in self.agents.items():
            status[agent_id] = {
                'healthy': agent.is_healthy(),
                'state': agent.state.value,
                'failed': agent_id in self.failed_agents,
                'load': self.agent_load.get(agent_id, 0),
                'retry_count': self.retry_counts.get(agent_id, 0),
                'capabilities': list(self.agent_capabilities.get(agent_id, set()))
            }
        return status
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent message history"""
        return list(self.message_history)[-limit:]
    
    def get_routing_performance(self) -> Dict[str, Any]:
        """Get routing performance metrics"""
        performance = {
            'routing_strategies': {},
            'agent_performance': {},
            'message_patterns': {}
        }
        
        # Analyze routing strategy effectiveness
        for rule in self.routing_rules:
            strategy_name = rule.strategy.value
            if strategy_name not in performance['routing_strategies']:
                performance['routing_strategies'][strategy_name] = {
                    'rules_count': 0,
                    'estimated_usage': 0
                }
            performance['routing_strategies'][strategy_name]['rules_count'] += 1
        
        # Agent performance analysis
        for agent_id, agent in self.agents.items():
            performance['agent_performance'][agent_id] = {
                'current_load': self.agent_load.get(agent_id, 0),
                'retry_count': self.retry_counts.get(agent_id, 0),
                'is_healthy': agent.is_healthy(),
                'capabilities_count': len(self.agent_capabilities.get(agent_id, set())),
                'response_time': agent.metrics.average_response_time,
                'message_count': agent.metrics.messages_processed
            }
        
        # Message pattern analysis
        performance['message_patterns'] = {
            'priority_distribution': {p.value: count for p, count in self.stats.messages_by_priority.items()},
            'type_distribution': {t.value: count for t, count in self.stats.messages_by_type.items()},
            'failure_rate': (self.stats.failed_routes / max(1, self.stats.total_messages)) * 100,
            'average_queue_size': self.get_queue_size()
        }
        
        return performance
    
    # =====================================
    # Configuration and Utilities
    # =====================================
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update bus configuration"""
        self.config.update(new_config)
        
        # Apply configuration changes
        if 'max_retries' in new_config:
            self.max_retries = new_config['max_retries']
        
        # Update message queue if needed
        if 'max_queue_size' in new_config:
            # Note: Changing queue size requires restart in this implementation
            logger.warning("Queue size change requires restart to take effect")
        
        logger.info("SynapticBus configuration updated")
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration"""
        return {
            'config': self.config.copy(),
            'routing_rules': [
                {
                    'pattern': rule.pattern,
                    'strategy': rule.strategy.value,
                    'target_agents': rule.target_agents,
                    'required_capabilities': list(rule.required_capabilities),
                    'priority_boost': rule.priority_boost
                }
                for rule in self.routing_rules
            ],
            'default_strategy': self.default_strategy.value,
            'agent_capabilities': {
                agent_id: list(caps) 
                for agent_id, caps in self.agent_capabilities.items()
            }
        }
    
    def import_configuration(self, config_data: Dict[str, Any]):
        """Import configuration from data"""
        if 'config' in config_data:
            self.update_config(config_data['config'])
        
        if 'routing_rules' in config_data:
            self.clear_routing_rules()
            for rule_data in config_data['routing_rules']:
                rule = RoutingRule(
                    pattern=rule_data['pattern'],
                    strategy=RoutingStrategy(rule_data['strategy']),
                    target_agents=rule_data.get('target_agents', []),
                    required_capabilities=set(rule_data.get('required_capabilities', [])),
                    priority_boost=rule_data.get('priority_boost', 0)
                )
                self.add_routing_rule(rule)
        
        if 'default_strategy' in config_data:
            self.default_strategy = RoutingStrategy(config_data['default_strategy'])
        
        logger.info("SynapticBus configuration imported")
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.stats = MessageStats()
        self.message_history.clear()
        logger.info("SynapticBus statistics reset")
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        healthy_agents = self.get_healthy_agents()
        total_agents = len(self.agents)
        
        health_summary = {
            'overall_status': 'healthy' if len(healthy_agents) == total_agents else 'degraded' if healthy_agents else 'critical',
            'agent_health': {
                'total_agents': total_agents,
                'healthy_agents': len(healthy_agents),
                'failed_agents': len(self.failed_agents),
                'health_percentage': (len(healthy_agents) / max(1, total_agents)) * 100
            },
            'message_performance': {
                'success_rate': (self.stats.successful_routes / max(1, self.stats.total_messages)) * 100,
                'average_latency': self.stats.average_latency,
                'queue_size': self.get_queue_size(),
                'total_processed': self.stats.total_messages
            },
            'system_load': {
                'total_load': sum(self.agent_load.values()),
                'average_load_per_agent': sum(self.agent_load.values()) / max(1, len(self.agents)),
                'max_load': max(self.agent_load.values()) if self.agent_load else 0,
                'load_distribution': dict(self.agent_load)
            },
            'recommendations': self._generate_health_recommendations(healthy_agents, total_agents)
        }
        
        return health_summary
    
    def _generate_health_recommendations(self, healthy_agents: List[str], total_agents: int) -> List[str]:
        """Generate health recommendations based on current state"""
        recommendations = []
        
        # Agent health recommendations
        if len(healthy_agents) < total_agents:
            failed_count = total_agents - len(healthy_agents)
            recommendations.append(f"⚠️ {failed_count} agents are unhealthy - investigate and restart failed agents")
        
        # Performance recommendations
        success_rate = (self.stats.successful_routes / max(1, self.stats.total_messages)) * 100
        if success_rate < 95:
            recommendations.append(f"📉 Message success rate is {success_rate:.1f}% - check agent capacity and network connectivity")
        
        # Queue size recommendations
        queue_size = self.get_queue_size()
        if queue_size > 100:
            recommendations.append(f"🚦 Message queue has {queue_size} pending messages - consider adding more workers or agents")
        
        # Load balancing recommendations
        if self.agent_load:
            max_load = max(self.agent_load.values())
            avg_load = sum(self.agent_load.values()) / len(self.agent_load)
            if max_load > avg_load * 3:  # One agent has 3x average load
                recommendations.append("⚖️ Load imbalance detected - review routing rules and agent capabilities")
        
        # Routing recommendations
        if not self.routing_rules:
            recommendations.append("📋 No routing rules configured - consider adding rules for better message routing")
        
        if not recommendations:
            recommendations.append("✅ System is operating optimally")
        
        return recommendations
    
    def __repr__(self) -> str:
        return f"<SynapticBus(agents={len(self.agents)}, queue_size={self.get_queue_size()}, running={self._running})>"

# =====================================
# Utility Functions
# =====================================

def create_routing_rule(pattern: Dict[str, Any], strategy: RoutingStrategy,
                       target_agents: List[str] = None,
                       required_capabilities: Set[str] = None,
                       priority_boost: int = 0) -> RoutingRule:
    """Utility function to create routing rules"""
    return RoutingRule(
        pattern=pattern,
        strategy=strategy,
        target_agents=target_agents or [],
        required_capabilities=required_capabilities or set(),
        priority_boost=priority_boost
    )

def create_capability_rule(required_capabilities: Set[str], 
                          priority_boost: int = 0) -> RoutingRule:
    """Create a capability-based routing rule"""
    return RoutingRule(
        pattern={},  # Match all messages
        strategy=RoutingStrategy.CAPABILITY_BASED,
        required_capabilities=required_capabilities,
        priority_boost=priority_boost
    )

def create_broadcast_rule(pattern: Dict[str, Any] = None) -> RoutingRule:
    """Create a broadcast routing rule"""
    return RoutingRule(
        pattern=pattern or {'recipient_id': '*'},
        strategy=RoutingStrategy.BROADCAST
    )

def create_load_balanced_rule(target_agents: List[str], 
                             pattern: Dict[str, Any] = None) -> RoutingRule:
    """Create a load-balanced routing rule"""
    return RoutingRule(
        pattern=pattern or {},
        strategy=RoutingStrategy.LOAD_BALANCED,
        target_agents=target_agents
    )

def create_round_robin_rule(target_agents: List[str],
                           pattern: Dict[str, Any] = None) -> RoutingRule:
    """Create a round-robin routing rule"""
    return RoutingRule(
        pattern=pattern or {},
        strategy=RoutingStrategy.ROUND_ROBIN,
        target_agents=target_agents
    )

# =====================================
# Factory Functions
# =====================================

def create_synaptic_bus(config: Dict[str, Any] = None) -> SynapticBus:
    """Factory function to create a configured SynapticBus"""
    return SynapticBus(config)

def create_basic_bus_with_rules() -> SynapticBus:
    """Create a SynapticBus with basic routing rules"""
    bus = SynapticBus()
    
    # Add common routing rules
    bus.add_routing_rule(create_broadcast_rule())
    bus.add_routing_rule(create_capability_rule({'decision_making'}))
    bus.add_routing_rule(create_capability_rule({'memory_management'}))
    
    return bus

def create_fault_tolerant_bus(max_retries: int = 5, num_workers: int = 6) -> SynapticBus:
    """Create a fault-tolerant SynapticBus with enhanced reliability"""
    config = {
        'max_retries': max_retries,
        'max_queue_size': 5000,
        'history_size': 2000
    }
    
    bus = SynapticBus(config)
    
    # Add fault-tolerance routing rules
    bus.add_routing_rule(RoutingRule(
        pattern={'priority': 4},  # Critical messages
        strategy=RoutingStrategy.LOAD_BALANCED,
        priority_boost=1
    ))
    
    return bus

# =====================================
# Bus Configuration Presets
# =====================================

def get_development_config() -> Dict[str, Any]:
    """Get configuration for development environment"""
    return {
        'max_retries': 2,
        'max_queue_size': 1000,
        'history_size': 500
    }

def get_production_config() -> Dict[str, Any]:
    """Get configuration for production environment"""
    return {
        'max_retries': 5,
        'max_queue_size': 10000,
        'history_size': 5000
    }

def get_high_throughput_config() -> Dict[str, Any]:
    """Get configuration for high-throughput scenarios"""
    return {
        'max_retries': 3,
        'max_queue_size': 50000,
        'history_size': 1000  # Smaller history for memory efficiency
    }

# =====================================
# Message Routing Helpers
# =====================================

def create_message_for_routing(sender_id: str, content: Dict[str, Any], 
                              routing_hints: Dict[str, Any] = None) -> Message:
    """Create a message with routing hints embedded"""
    from .base import Message, MessageType, MessagePriority
    
    # Embed routing hints in message content
    enhanced_content = content.copy()
    if routing_hints:
        enhanced_content.update(routing_hints)
    
    return Message(
        type=MessageType.REQUEST,
        priority=MessagePriority.NORMAL,
        sender_id=sender_id,
        recipient_id=routing_hints.get('preferred_recipient', '*'),
        content=enhanced_content
    )

def extract_routing_metadata(message: Message) -> Dict[str, Any]:
    """Extract routing-relevant metadata from a message"""
    return {
        'message_id': message.id,
        'type': message.type.value,
        'priority': message.priority.value,
        'sender': message.sender_id,
        'recipient': message.recipient_id,
        'content_keys': list(message.content.keys()),
        'has_correlation': message.correlation_id is not None,
        'is_reply': message.reply_to is not None,
        'timestamp': message.timestamp
    }
