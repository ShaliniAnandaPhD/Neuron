
"""
Neuron Framework: Core Base Classes

Fundamental classes for the Neuron framework including Message, BaseAgent, 
and core data structures.
"""

import json
import uuid
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import threading
from collections import defaultdict, deque

# Configure logging
logger = logging.getLogger(__name__)

# =====================================
# Core Enums and Types
# =====================================

class MessagePriority(Enum):
    """Message priority levels for routing and processing"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"

class MemoryType(Enum):
    """Types of memory systems available to agents"""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"

class MessageType(Enum):
    """Types of messages in the system"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    COORDINATION = "coordination"
    HEALTH_CHECK = "health_check"
    ERROR = "error"

# =====================================
# Core Data Structures
# =====================================

@dataclass
class Message:
    """
    Core message structure for agent communication
    
    This is the fundamental communication unit in the Neuron framework.
    All agent interactions happen through structured Message objects.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    sender_id: str = ""
    recipient_id: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        result = asdict(self)
        result['type'] = self.type.value
        result['priority'] = self.priority.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        # Convert enum strings back to enums
        if 'type' in data:
            data['type'] = MessageType(data['type'])
        if 'priority' in data:
            data['priority'] = MessagePriority(data['priority'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def create_reply(self, content: Dict[str, Any], 
                    message_type: MessageType = MessageType.RESPONSE) -> 'Message':
        """Create a reply message to this message"""
        return Message(
            type=message_type,
            priority=self.priority,
            sender_id=self.recipient_id,
            recipient_id=self.sender_id,
            content=content,
            correlation_id=self.id,
            reply_to=self.id
        )

@dataclass
class AgentCapabilities:
    """Defines what an agent can do"""
    capabilities: Set[str] = field(default_factory=set)
    memory_types: Set[MemoryType] = field(default_factory=set)
    max_concurrent_tasks: int = 10
    supported_message_types: Set[MessageType] = field(
        default_factory=lambda: {MessageType.REQUEST, MessageType.RESPONSE}
    )
    
    def can_handle(self, capability: str) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities
    
    def has_memory_type(self, memory_type: MemoryType) -> bool:
        """Check if agent supports a memory type"""
        return memory_type in self.memory_types

@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    messages_processed: int = 0
    messages_sent: int = 0
    errors_count: int = 0
    average_response_time: float = 0.0
    last_activity: float = field(default_factory=time.time)
    uptime_start: float = field(default_factory=time.time)
    confidence_score: float = 1.0  # Agent's confidence in its responses
    
    def update_response_time(self, response_time: float):
        """Update average response time with new measurement"""
        if self.messages_processed == 0:
            self.average_response_time = response_time
        else:
            # Running average
            total_time = self.average_response_time * self.messages_processed
            self.average_response_time = (total_time + response_time) / (self.messages_processed + 1)
    
    def get_uptime(self) -> float:
        """Get uptime in seconds"""
        return time.time() - self.uptime_start

# =====================================
# Memory Interface
# =====================================

class MemoryInterface(ABC):
    """Abstract interface for memory systems"""
    
    @abstractmethod
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store information in memory"""
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from memory"""
        pass
    
    @abstractmethod
    async def search(self, query: Dict[str, Any]) -> List[Any]:
        """Search memory with query"""
        pass
    
    @abstractmethod
    async def forget(self, key: str) -> bool:
        """Remove information from memory"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all memory"""
        pass

# =====================================
# Base Agent Class
# =====================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Neuron framework
    
    This class provides the fundamental structure and interface that all
    agents must implement. It handles message processing, state management,
    and basic coordination protocols.
    """
    
    def __init__(self, 
                 agent_id: str,
                 capabilities: AgentCapabilities = None,
                 config: Dict[str, Any] = None):
        """
        Initialize the base agent
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: What this agent can do
            config: Configuration parameters
        """
        self.agent_id = agent_id
        self.capabilities = capabilities or AgentCapabilities()
        self.config = config or {}
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()
        
        # Message handling
        self.message_queue: deque = deque()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # Memory systems
        self.memory_systems: Dict[MemoryType, MemoryInterface] = {}
        
        # Coordination
        self.synaptic_bus = None  # Will be set by the circuit
        self.known_agents: Dict[str, AgentCapabilities] = {}
        
        # Event hooks
        self.event_hooks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Setup default message handlers
        self._setup_default_handlers()
        
        logger.info(f"Agent {self.agent_id} initialized with capabilities: {self.capabilities.capabilities}")
    
    def _setup_default_handlers(self):
        """Setup default message handlers"""
        self.message_handlers[MessageType.HEALTH_CHECK] = self._handle_health_check
        self.message_handlers[MessageType.REQUEST] = self._handle_request
        self.message_handlers[MessageType.RESPONSE] = self._handle_response
        self.message_handlers[MessageType.COORDINATION] = self._handle_coordination
        self.message_handlers[MessageType.ERROR] = self._handle_error
    
    # =====================================
    # State Management
    # =====================================
    
    def get_state(self) -> AgentState:
        """Get current agent state"""
        with self._lock:
            return self.state
    
    def set_state(self, new_state: AgentState):
        """Set agent state and trigger events"""
        old_state = self.state
        with self._lock:
            self.state = new_state
        
        if old_state != new_state:
            self._trigger_event('state_changed', {
                'old_state': old_state,
                'new_state': new_state,
                'timestamp': time.time()
            })
            logger.info(f"Agent {self.agent_id} state changed: {old_state.value} -> {new_state.value}")
    
    def is_healthy(self) -> bool:
        """Check if agent is in a healthy state"""
        return self.state in [AgentState.ACTIVE, AgentState.BUSY]
    
    # =====================================
    # Memory Management
    # =====================================
    
    def add_memory_system(self, memory_type: MemoryType, memory_system: MemoryInterface):
        """Add a memory system to this agent"""
        self.memory_systems[memory_type] = memory_system
        self.capabilities.memory_types.add(memory_type)
        logger.debug(f"Agent {self.agent_id} added {memory_type.value} memory system")
    
    async def remember(self, memory_type: MemoryType, key: str, value: Any, 
                      metadata: Dict[str, Any] = None) -> bool:
        """Store information in specified memory type"""
        if memory_type not in self.memory_systems:
            logger.warning(f"Agent {self.agent_id} doesn't have {memory_type.value} memory")
            return False
        
        try:
            return await self.memory_systems[memory_type].store(key, value, metadata)
        except Exception as e:
            logger.error(f"Agent {self.agent_id} memory store error: {e}")
            return False
    
    async def recall(self, memory_type: MemoryType, key: str) -> Optional[Any]:
        """Retrieve information from specified memory type"""
        if memory_type not in self.memory_systems:
            return None
        
        try:
            return await self.memory_systems[memory_type].retrieve(key)
        except Exception as e:
            logger.error(f"Agent {self.agent_id} memory recall error: {e}")
            return None
    
    async def search_memory(self, memory_type: MemoryType, query: Dict[str, Any]) -> List[Any]:
        """Search memory with query"""
        if memory_type not in self.memory_systems:
            return []
        
        try:
            return await self.memory_systems[memory_type].search(query)
        except Exception as e:
            logger.error(f"Agent {self.agent_id} memory search error: {e}")
            return []
    
    # =====================================
    # Message Processing
    # =====================================
    
    async def send_message(self, message: Message) -> bool:
        """Send a message through the synaptic bus"""
        if not self.synaptic_bus:
            logger.error(f"Agent {self.agent_id} has no synaptic bus connection")
            return False
        
        message.sender_id = self.agent_id
        
        try:
            success = await self.synaptic_bus.route_message(message)
            if success:
                self.metrics.messages_sent += 1
                self._trigger_event('message_sent', {'message': message})
            return success
        except Exception as e:
            logger.error(f"Agent {self.agent_id} send message error: {e}")
            return False
    
    async def receive_message(self, message: Message) -> bool:
        """Receive and queue a message for processing"""
        if message.is_expired():
            logger.warning(f"Agent {self.agent_id} received expired message: {message.id}")
            return False
        
        with self._lock:
            self.message_queue.append(message)
        
        self._trigger_event('message_received', {'message': message})
        
        # Process message asynchronously
        task = asyncio.create_task(self._process_message(message))
        self.active_tasks[message.id] = task
        
        return True
    
    async def _process_message(self, message: Message):
        """Process a single message"""
        start_time = time.time()
        
        try:
            self.set_state(AgentState.BUSY)
            
            # Find appropriate handler
            handler = self.message_handlers.get(message.type)
            if not handler:
                logger.warning(f"Agent {self.agent_id} has no handler for {message.type.value}")
                await self._send_error_response(message, "No handler for message type")
                return
            
            # Process the message
            response = await handler(message)
            
            # Send response if needed
            if response and message.type == MessageType.REQUEST:
                if isinstance(response, dict):
                    reply = message.create_reply(response)
                    await self.send_message(reply)
                elif isinstance(response, Message):
                    await self.send_message(response)
            
            # Update metrics
            response_time = time.time() - start_time
            self.metrics.update_response_time(response_time)
            self.metrics.messages_processed += 1
            self.metrics.last_activity = time.time()
            
            self._trigger_event('message_processed', {
                'message': message,
                'response_time': response_time
            })
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} message processing error: {e}")
            self.metrics.errors_count += 1
            await self._send_error_response(message, str(e))
            
        finally:
            # Clean up task
            if message.id in self.active_tasks:
                del self.active_tasks[message.id]
            
            # Return to active state if no other tasks
            if not self.active_tasks:
                self.set_state(AgentState.ACTIVE)
    
    async def _send_error_response(self, original_message: Message, error_msg: str):
        """Send an error response for a failed message"""
        error_response = original_message.create_reply(
            content={'error': error_msg, 'timestamp': time.time()},
            message_type=MessageType.ERROR
        )
        await self.send_message(error_response)
    
    # =====================================
    # Default Message Handlers
    # =====================================
    
    async def _handle_health_check(self, message: Message) -> Dict[str, Any]:
        """Handle health check messages"""
        return {
            'agent_id': self.agent_id,
            'state': self.state.value,
            'healthy': self.is_healthy(),
            'metrics': asdict(self.metrics),
            'capabilities': {
                'capabilities': list(self.capabilities.capabilities),
                'memory_types': [mt.value for mt in self.capabilities.memory_types]
            },
            'timestamp': time.time()
        }
    
    async def _handle_coordination(self, message: Message) -> Optional[Dict[str, Any]]:
        """Handle coordination messages"""
        coord_type = message.content.get('coordination_type')
        
        if coord_type == 'agent_discovery':
            # Another agent is announcing itself
            agent_id = message.content.get('agent_id')
            capabilities = message.content.get('capabilities')
            if agent_id and capabilities:
                self.known_agents[agent_id] = AgentCapabilities(**capabilities)
                logger.info(f"Agent {self.agent_id} discovered agent {agent_id}")
            
            # Respond with our own capabilities
            return {
                'coordination_type': 'agent_announcement',
                'agent_id': self.agent_id,
                'capabilities': {
                    'capabilities': list(self.capabilities.capabilities),
                    'memory_types': [mt.value for mt in self.capabilities.memory_types],
                    'max_concurrent_tasks': self.capabilities.max_concurrent_tasks
                }
            }
        
        elif coord_type == 'agent_announcement':
            # Store information about another agent
            agent_id = message.content.get('agent_id')
            capabilities = message.content.get('capabilities')
            if agent_id and capabilities:
                # Convert memory_types back to enums
                if 'memory_types' in capabilities:
                    capabilities['memory_types'] = {
                        MemoryType(mt) for mt in capabilities['memory_types']
                    }
                if 'capabilities' in capabilities:
                    capabilities['capabilities'] = set(capabilities['capabilities'])
                
                self.known_agents[agent_id] = AgentCapabilities(**capabilities)
                logger.info(f"Agent {self.agent_id} learned about agent {agent_id}")
        
        return None
    
    async def _handle_error(self, message: Message) -> None:
        """Handle error messages"""
        error_info = message.content.get('error', 'Unknown error')
        logger.error(f"Agent {self.agent_id} received error: {error_info}")
        self._trigger_event('error_received', {'message': message})
    
    # =====================================
    # Abstract Methods - Must be implemented by subclasses
    # =====================================
    
    @abstractmethod
    async def _handle_request(self, message: Message) -> Optional[Dict[str, Any]]:
        """Handle request messages - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _handle_response(self, message: Message) -> None:
        """Handle response messages - must be implemented by subclasses"""
        pass
    
    # =====================================
    # Agent Lifecycle
    # =====================================
    
    async def start(self):
        """Start the agent"""
        self.set_state(AgentState.ACTIVE)
        self._trigger_event('agent_started', {'timestamp': time.time()})
        logger.info(f"Agent {self.agent_id} started")
        
        # Announce ourselves to other agents
        if self.synaptic_bus:
            discovery_message = Message(
                type=MessageType.COORDINATION,
                sender_id=self.agent_id,
                recipient_id="*",  # Broadcast
                content={
                    'coordination_type': 'agent_discovery',
                    'agent_id': self.agent_id,
                    'capabilities': {
                        'capabilities': list(self.capabilities.capabilities),
                        'memory_types': [mt.value for mt in self.capabilities.memory_types],
                        'max_concurrent_tasks': self.capabilities.max_concurrent_tasks
                    }
                }
            )
            await self.send_message(discovery_message)
    
    async def stop(self):
        """Stop the agent gracefully"""
        self.set_state(AgentState.SHUTTING_DOWN)
        
        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Agent {self.agent_id} waiting for {len(self.active_tasks)} tasks to complete")
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        # Clear message queue
        with self._lock:
            self.message_queue.clear()
        
        self._trigger_event('agent_stopped', {'timestamp': time.time()})
        logger.info(f"Agent {self.agent_id} stopped")
    
    # =====================================
    # Event System
    # =====================================
    
    def add_event_hook(self, event_name: str, callback: Callable):
        """Add an event hook"""
        self.event_hooks[event_name].append(callback)
    
    def remove_event_hook(self, event_name: str, callback: Callable):
        """Remove an event hook"""
        if callback in self.event_hooks[event_name]:
            self.event_hooks[event_name].remove(callback)
    
    def _trigger_event(self, event_name: str, event_data: Dict[str, Any]):
        """Trigger event hooks"""
        for callback in self.event_hooks[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self, event_data))
                else:
                    callback(self, event_data)
            except Exception as e:
                logger.error(f"Agent {self.agent_id} event hook error: {e}")
    
    # =====================================
    # Utility Methods
    # =====================================
    
    def find_agent_with_capability(self, capability: str) -> Optional[str]:
        """Find an agent that has a specific capability"""
        for agent_id, agent_caps in self.known_agents.items():
            if agent_caps.can_handle(capability):
                return agent_id
        return None
    
    def get_agents_with_memory_type(self, memory_type: MemoryType) -> List[str]:
        """Get list of agents that have a specific memory type"""
        agents = []
        for agent_id, agent_caps in self.known_agents.items():
            if agent_caps.has_memory_type(memory_type):
                agents.append(agent_id)
        return agents
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        return {
            'agent_id': self.agent_id,
            'state': self.state.value,
            'healthy': self.is_healthy(),
            'capabilities': {
                'capabilities': list(self.capabilities.capabilities),
                'memory_types': [mt.value for mt in self.capabilities.memory_types],
                'max_concurrent_tasks': self.capabilities.max_concurrent_tasks
            },
            'metrics': asdict(self.metrics),
            'active_tasks': len(self.active_tasks),
            'queue_size': len(self.message_queue),
            'known_agents': list(self.known_agents.keys()),
            'timestamp': time.time()
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, state={self.state.value})>"

# =====================================
# Utility Functions
# =====================================

def create_message(sender_id: str, recipient_id: str, content: Dict[str, Any],
                  message_type: MessageType = MessageType.REQUEST,
                  priority: MessagePriority = MessagePriority.NORMAL) -> Message:
    """Utility function to create a message"""
    return Message(
        type=message_type,
        priority=priority,
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content
    )

def serialize_message(message: Message) -> str:
    """Serialize a message to JSON string"""
    return json.dumps(message.to_dict())

def deserialize_message(json_str: str) -> Message:
    """Deserialize a message from JSON string"""
    data = json.loads(json_str)
    return Message.from_dict(data)
